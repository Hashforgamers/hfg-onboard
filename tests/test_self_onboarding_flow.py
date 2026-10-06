"""Onboarding integration tests: real Flask/ORM, isolated DB, mocked external IO."""
import io
import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from flask import Flask
from werkzeug.security import check_password_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from controllers import controllers as routes
from db.extensions import db, mail
from services.services import VendorService
from models.vendor import Vendor
from models.vendorStatus import VendorStatus
from models.passwordManager import PasswordManager
from models.vendorDaySlotConfig import VendorDaySlotConfig
from models.slots import Slot


class MemoryRedis:
    def __init__(self):
        self.values = {'self_onboard:verify_token:proof': 'owner@example.test'}
    def get(self, key):
        return self.values.get(key)
    def setex(self, key, ttl, value):
        self.values[key] = value
    def set(self, key, value, **kwargs):
        if kwargs.get('nx') and key in self.values:
            return False
        self.values[key] = value
        return True
    def eval(self, script, count, key, value):
        if self.values.get(key) != value:
            return 0
        del self.values[key]
        return 1


@pytest.fixture
def app(monkeypatch, tmp_path):
    app = Flask(__name__)
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=f'sqlite:///{tmp_path / "onboard.db"}', MAIL_SUPPRESS_SEND=True,
                      MAIL_DEFAULT_SENDER='test@example.test', MAX_CONTENT_LENGTH=34 * 1024 * 1024)
    db.init_app(app)
    mail.init_app(app)
    app.register_blueprint(routes.vendor_bp, url_prefix='/api')
    monkeypatch.setattr(routes, 'redis_client', MemoryRedis())
    # PostgreSQL-specific per-vendor DDL is separately checked for deferred commit.
    for name in ('slot', 'console_availability', 'dashboard', 'promo'):
        monkeypatch.setattr(VendorService, f'create_vendor_{name}_table', Mock())
    monkeypatch.setattr(routes.CloudinaryGameImageService, 'upload_vendor_document',
                        lambda *args: {'success': True, 'url': 'https://example.test/document', 'public_id': 'test'})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def payload():
    return dict(onboarding_source='self_onboard', self_onboard_email_verification_token='proof',
                cafe_name='Test Cafe', owner_name='Test Owner', vendor_account_email='other@example.test',
                contact_info={'email': 'owner@example.test', 'phone': '9876543210'},
                physicalAddress={'street': 'Test Street', 'city': 'Pune', 'state': 'Maharashtra',
                                 'zipCode': '411001', 'country': 'India', 'latitude': 18.5, 'longitude': 73.8},
                business_registration_details={'registration_number': 'TEST-123', 'registration_type': 'GST'},
                owner_proof_details={'type': 'Passport', 'number': 'TEST1234'},
                document_submitted={key: True for key in routes.ALLOWED_VENDOR_DOCUMENT_TYPES},
                timing={'mon': {'open': '09:00 AM', 'close': '11:00 AM', 'closed': False, 'slot_duration': 60},
                        'tue': {'open': '01:00 PM', 'close': '02:00 PM', 'closed': False, 'slot_duration': 30}},
                available_games=[{'name': 'pc', 'total_slot': 1, 'rate_per_slot': 50}], amenities={})


def submit(app, data=None):
    form = {'json': json.dumps(data or payload())}
    form.update({key: (io.BytesIO(b'%PDF-1.4 test'), f'{key}.pdf') for key in routes.ALLOWED_VENDOR_DOCUMENT_TYPES})
    return app.test_client().post('/api/onboard', data=form, content_type='multipart/form-data')


def test_active_cafe_credentials_and_schedule(app):
    with mail.record_messages() as messages:
        response = submit(app)
    assert response.status_code == 201, response.json
    assert response.json['status'] == 'active'
    assert response.json['email_sent'] is True
    vendor = Vendor.query.one()
    assert vendor.account.email == 'owner@example.test'
    assert VendorStatus.query.one().status == 'active'
    assert len(messages) == 1
    body = messages[0].body
    password = next(line.removeprefix('Password: ') for line in body.splitlines() if line.startswith('Password: '))
    assert check_password_hash(PasswordManager.query.one().password, password)
    assert 'Vendor PIN:' in body and 'Status: Active' in body and 'buy a plan' in body
    assert [row.slot_duration for row in VendorDaySlotConfig.query.order_by(VendorDaySlotConfig.day)] == [60, 30]
    assert Slot.query.count() == 4
    assert routes.redis_client.get('self_onboard:verify_token:proof') is None
    # Run the real login-service against the freshly onboarded account in a
    # separate interpreter because both services use top-level models packages.
    pin = next(line.removeprefix('Vendor PIN: ') for line in body.splitlines() if line.startswith('Vendor PIN: '))
    login_script = """
import json, sys
from flask import Flask
from app import create_app
from app.extension import db
from routes import auth_routes
uri, email, password, pin, vendor_id = json.load(sys.stdin)
app = Flask(__name__)
app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI=uri)
db.init_app(app)
auth_routes._PASSWORD_FLAG_COLUMN_READY = True
app.register_blueprint(auth_routes.auth_bp, url_prefix='/api')
client = app.test_client()
response = client.post('/api/login', json=dict(email=email, password=password, parent_type='vendor'))
assert response.status_code == 200, response.json
assert response.json['status'] == 'success', response.json
assert response.json['vendors'][0]['id'] == vendor_id
response = client.post('/api/validatePin', json=dict(vendor_id=vendor_id, pin=pin))
assert response.status_code == 200, response.json
assert response.json['data']['token']
print('Login and PIN passed')
"""
    result = subprocess.run([sys.executable, '-c', login_script],
        input=json.dumps([app.config['SQLALCHEMY_DATABASE_URI'], vendor.account.email, password, pin, vendor.id]),
        text=True, capture_output=True, cwd=Path(__file__).resolve().parents[2] / 'hfg-login-service')
    assert result.returncode == 0, result.stdout + result.stderr
    assert submit(app).status_code == 409


def test_document_failure_rolls_back_and_can_retry(app, monkeypatch):
    original = routes.CloudinaryGameImageService.upload_vendor_document
    monkeypatch.setattr(routes.CloudinaryGameImageService, 'upload_vendor_document', Mock(side_effect=RuntimeError('offline')))
    assert submit(app).status_code == 502
    assert Vendor.query.count() == 0
    assert PasswordManager.query.count() == 0
    assert routes.redis_client.get('self_onboard:verify_token:proof') == 'owner@example.test'
    monkeypatch.setattr(routes.CloudinaryGameImageService, 'upload_vendor_document', original)
    assert submit(app).status_code == 201


def test_email_failure_preserves_account_and_reports_failure(app, monkeypatch):
    monkeypatch.setattr(mail, 'send', Mock(side_effect=RuntimeError('mail unavailable')))
    response = submit(app)
    assert response.status_code == 201
    assert response.json['email_sent'] is False
    assert 'Do not submit' in response.json['message']
    assert VendorStatus.query.one().status == 'active'
    assert PasswordManager.query.count() == 1


def test_invalid_token_cannot_create_account(app):
    data = payload()
    data['self_onboard_email_verification_token'] = 'wrong'
    assert submit(app, data).status_code == 400
    assert Vendor.query.count() == 0


def test_invalid_json_shape(app):
    assert app.test_client().post('/api/onboard', data={'json': '[]'}).status_code == 400


def test_welcome_html_escapes_owner_data(app):
    vendor = Mock(id=1, cafe_name='<script>bad</script>', owner_name='<owner>')
    html = VendorService.build_welcome_email_html(vendor, 'secret', 'owner@example.test', '1234', activated=True)
    assert '<script>' not in html and '&lt;owner&gt;' in html


def test_four_large_documents_bypass_proxy_limit(app):
    form = {'json': json.dumps(payload())}
    form.update({key: (io.BytesIO(b'%PDF-1.4\n' + b' ' * (8 * 1024 * 1024 - 9)), f'{key}.pdf')
                 for key in routes.ALLOWED_VENDOR_DOCUMENT_TYPES})
    response = app.test_client().post('/api/onboard', data=form)
    assert response.status_code == 201, response.json


def test_oversized_file_preserves_verification(app):
    form = {'json': json.dumps(payload())}
    form.update({key: (io.BytesIO(b'x' * (8 * 1024 * 1024 + 1)), f'{key}.pdf')
                 for key in routes.ALLOWED_VENDOR_DOCUMENT_TYPES})
    response = app.test_client().post('/api/onboard', data=form)
    assert response.status_code == 400
    assert 'Max 8 MB' in response.json['message']
    assert Vendor.query.count() == 0
    assert routes.redis_client.get('self_onboard:verify_token:proof')


def test_partial_upload_cleanup_and_retry(app, monkeypatch):
    destroy = Mock(return_value={'result': 'ok'})
    monkeypatch.setattr('cloudinary.uploader.destroy', destroy)
    uploader = Mock(side_effect=[{'success': True, 'url': 'https://example.test/doc',
                                 'public_id': 'attempt-only', 'resource_type': 'raw'}, RuntimeError('offline')])
    monkeypatch.setattr(routes.CloudinaryGameImageService, 'upload_vendor_document', uploader)
    response = submit(app)
    assert response.status_code == 502
    assert response.json['request_id']
    assert Vendor.query.count() == 0
    destroy.assert_called_once_with('attempt-only', resource_type='raw')
    assert routes.redis_client.get('self_onboard:verify_token:proof')


def test_commit_failure_cleans_documents(app, monkeypatch):
    destroy = Mock(return_value={'result': 'ok'})
    monkeypatch.setattr('cloudinary.uploader.destroy', destroy)
    original = db.session.commit
    monkeypatch.setattr(db.session, 'commit', Mock(side_effect=RuntimeError('commit failed')))
    response = submit(app)
    assert response.status_code == 500
    assert Vendor.query.count() == 0
    assert destroy.call_count == 4
    monkeypatch.setattr(db.session, 'commit', original)
    assert submit(app).status_code == 201


@pytest.mark.parametrize('filename,content', [('bad.exe', b'test'), ('empty.pdf', b'')])
def test_invalid_documents(app, filename, content):
    form = {'json': json.dumps(payload())}
    form.update({key: (io.BytesIO(content), filename) for key in routes.ALLOWED_VENDOR_DOCUMENT_TYPES})
    response = app.test_client().post('/api/onboard', data=form)
    assert response.status_code == 400
    assert Vendor.query.count() == 0
    assert routes.redis_client.get('self_onboard:verify_token:proof')


def test_real_app_large_request_json_and_cors(monkeypatch, tmp_path):
    from app import create_app
    from app.config import Config
    monkeypatch.setattr(Config, 'SQLALCHEMY_DATABASE_URI', f'sqlite:///{tmp_path / "limits.db"}')
    monkeypatch.setattr(Config, 'SQLALCHEMY_ENGINE_OPTIONS', {})
    monkeypatch.setattr(Config, 'APP_ENV', 'development')
    app = create_app()
    client = app.test_client()
    response = client.post('/api/onboard', data=b'x' * (35 * 1024 * 1024),
                           content_type='multipart/form-data; boundary=test',
                           headers={'Origin': 'https://onboard.hashforgamers.com'})
    assert response.status_code == 413
    assert '8 MB' in response.json['message']
    assert response.headers['X-Request-Id']
    assert 'X-Request-Id' in response.headers['Access-Control-Expose-Headers']
    preflight = client.options('/api/onboard', headers={
        'Origin': 'https://onboard.hashforgamers.com',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
    })
    assert preflight.status_code == 200
    assert preflight.headers['Access-Control-Allow-Origin']
