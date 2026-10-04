"""Exercise the actual schedule handler/helpers with an isolated SQL database."""
import ast
import os
import uuid
from pathlib import Path
from datetime import datetime, date, timedelta, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import jwt
import pytest
from flask import Flask, request, jsonify, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, tuple_, func, bindparam


@pytest.fixture
def setup():
    app = Flask(__name__)
    url = os.getenv('HOURS_TEST_DATABASE_URL', 'sqlite://')
    schema = 'hours_test_' + uuid.uuid4().hex
    app.config.update(SQLALCHEMY_DATABASE_URI=url, JWT_SECRET_KEY='test-hours-key-' * 4)
    if url.startswith('postgresql'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'options': f'-csearch_path={schema}'}}
    db = SQLAlchemy(app)
    class Vendor(db.Model):
        __tablename__ = 'vendors'
        id = db.Column(db.Integer, primary_key=True)
    class AvailableGame(db.Model):
        __tablename__ = 'available_games'
        id = db.Column(db.Integer, primary_key=True)
        vendor_id = db.Column(db.Integer)
        total_slot = db.Column(db.Integer)
    class Slot(db.Model):
        __tablename__ = 'slots'
        id = db.Column(db.Integer, primary_key=True)
        gaming_type_id = db.Column(db.Integer)
        start_time = db.Column(db.Time)
        end_time = db.Column(db.Time)
        available_slot = db.Column(db.Integer)
        is_available = db.Column(db.Boolean)
    source = Path(__file__).resolve().parents[1] / 'controllers/controllers.py'
    tree = ast.parse(source.read_text())
    names = {'normalize_day_key', 'parse_time_flexible', '_generate_blocks', '_apply_slot_rows_for_day',
             '_authorize_hours_owner', 'update_slot'}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    for node in nodes:
        node.decorator_list = []
    scope = dict(db=db, Vendor=Vendor, AvailableGame=AvailableGame, Slot=Slot,
        request=request, jsonify=jsonify, current_app=current_app, os=os,
        text=text, tuple_=tuple_, func=func, bindparam=bindparam, dt=datetime, date=date,
        dtime=time, timedelta=timedelta, IST=ZoneInfo('Asia/Kolkata'), FUTURE_WINDOW_DAYS=60,
        WEEKDAY_MAP=dict(zip(['mon','tue','wed','thu','fri','sat','sun'], range(7))),
        FULL_DAY_TO_SHORT={day: day[:3] for day in ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']})
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), scope)
    app.add_url_rule('/api/vendor/<int:vendor_id>/updateSlot', view_func=scope['update_slot'], methods=['POST'])
    with app.app_context():
        if url.startswith('postgresql'):
            with db.engine.begin() as conn: conn.execute(text(f'CREATE SCHEMA {schema}'))
        db.create_all()
        for sql in [
            'CREATE TABLE vendor_day_slot_config (vendor_id INT, day TEXT, opening_time TEXT, closing_time TEXT, slot_duration INT, UNIQUE(vendor_id,day))',
            'CREATE TABLE opening_days (vendor_id INT, day TEXT, is_open BOOLEAN)',
            'CREATE TABLE bookings (id INT, slot_id INT, status TEXT)',
            'CREATE TABLE transactions (booking_id INT, booked_date DATE)',
            'CREATE TABLE vendor_1_slot (vendor_id INT, slot_id INT, date DATE, available_slot INT, is_available BOOLEAN, PRIMARY KEY(vendor_id,date,slot_id))',
        ]: db.session.execute(text(sql))
        db.session.add_all([Vendor(id=1), Vendor(id=2), AvailableGame(id=1,vendor_id=1,total_slot=3)])
        db.session.commit()
        token = jwt.encode({'sub': {'id': 1, 'type': 'vendor'}, 'exp': datetime.now()+timedelta(hours=1)}, app.config['JWT_SECRET_KEY'], algorithm='HS256')
        yield SimpleNamespace(app=app, db=db, Slot=Slot, token=token, scope=scope)
        db.session.remove()
        if url.startswith('postgresql'):
            with db.engine.begin() as conn: conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        else:
            db.drop_all()
        db.engine.dispose()


def save(e, **changes):
    payload = dict(day='monday', start_time='09:00', end_time='11:00', slot_duration=60,
                   is_enabled=True, start_date='2026-10-05', window_days=7)
    payload.update(changes)
    return e.app.test_client().post('/api/vendor/1/updateSlot', json=payload,
                                  headers={'Authorization': 'Bearer '+e.token})


def test_save_reload_closed_reopen_and_far_future(setup):
    e = setup
    result = save(e)
    assert result.status_code == 200, result.json
    assert result.json['operatingHours'] == dict(day='mon',open='09:00',close='11:00',slotDurationMinutes=60,isEnabled=True,is24Hours=False)
    assert e.db.session.execute(text('SELECT COUNT(*) FROM vendor_1_slot')).scalar() == 2
    e.db.session.execute(text("INSERT INTO vendor_1_slot SELECT vendor_id,slot_id,'2026-12-07',available_slot,is_available FROM vendor_1_slot"))
    e.db.session.commit()
    assert save(e, is_enabled=False).status_code == 200
    assert e.db.session.execute(text('SELECT COUNT(*) FROM vendor_1_slot')).scalar() == 0
    assert e.db.session.execute(text('SELECT is_open FROM opening_days')).scalar() == 0
    assert save(e).status_code == 200
    assert e.db.session.execute(text('SELECT COUNT(*) FROM vendor_1_slot')).scalar() == 2


def test_capacity_is_preserved_and_conflicts_roll_back(setup):
    e = setup
    assert save(e).status_code == 200
    e.db.session.execute(text('UPDATE vendor_1_slot SET available_slot=2 WHERE slot_id=1'))
    e.db.session.commit()
    assert save(e).status_code == 200
    assert e.db.session.execute(text('SELECT available_slot FROM vendor_1_slot WHERE slot_id=1')).scalar() == 2
    for changes in [dict(is_enabled=False),dict(start_time='10:00'),dict(slot_duration=30)]:
        result = save(e, **changes)
        assert result.status_code == 409, result.json
        assert e.db.session.execute(text('SELECT is_open FROM opening_days')).scalar() == 1
        assert e.db.session.execute(text('SELECT opening_time FROM vendor_day_slot_config')).scalar() == '09:00 AM'
    assert e.db.session.execute(text('SELECT COUNT(*) FROM vendor_1_slot')).scalar() == 2


@pytest.mark.parametrize('changes,count', [(dict(start_time='22:00',end_time='02:00'),4),(dict(is_24_hours=True),24)])
def test_overnight_and_full_day(setup, changes, count):
    result = save(setup, **changes)
    assert result.status_code == 200, result.json
    assert setup.db.session.execute(text('SELECT COUNT(*) FROM vendor_1_slot')).scalar() == count


@pytest.mark.parametrize('changes', [dict(is_enabled='false'),dict(slot_duration=15.5),dict(window_days=True),
    dict(day='noday'),dict(day=['mon']),dict(window_days=1.5),dict(start_time='25:00'),dict(end_time='09:10'),dict(slot_duration=True)])
def test_invalid_input_does_not_write(setup, changes):
    assert save(setup, **changes).status_code == 400
    assert setup.db.session.execute(text('SELECT COUNT(*) FROM vendor_day_slot_config')).scalar() == 0


def test_owner_scope_and_json_validation(setup):
    e = setup
    client = e.app.test_client()
    assert client.post('/api/vendor/1/updateSlot', json={}).status_code == 401
    headers = {'Authorization': 'Bearer '+e.token}
    assert client.post('/api/vendor/2/updateSlot', json={}, headers=headers).status_code == 403
    assert client.post('/api/vendor/1/updateSlot', json=[], headers=headers).status_code == 400
    assert client.post('/api/vendor/1/updateSlot', json={}, headers={'Authorization':'Bearer broken'}).status_code == 401


def test_cafe_without_games_can_save_configuration(setup):
    e = setup
    e.db.session.query(e.scope['AvailableGame']).delete()
    e.db.session.commit()
    assert save(e).status_code == 200
    assert e.db.session.execute(text('SELECT COUNT(*) FROM vendor_day_slot_config')).scalar() == 1


def test_booking_conflict_detected_even_if_capacity_was_stale(setup):
    e = setup
    assert save(e).status_code == 200
    e.db.session.execute(text("INSERT INTO bookings VALUES (1,1,'confirmed')"))
    e.db.session.execute(text("INSERT INTO transactions VALUES (1,'2026-10-05')"))
    e.db.session.commit()
    assert save(e, is_enabled=False).status_code == 409
    assert e.db.session.execute(text('SELECT COUNT(*) FROM vendor_1_slot')).scalar() == 2


def test_future_extension_uses_saved_weekday_grid_not_old_templates(setup, monkeypatch):
    import sys
    import types
    e = setup
    assert save(e).status_code == 200
    source = Path(__file__).resolve().parents[1] / 'services/services.py'
    tree = ast.parse(source.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'VendorService')
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'extend_vendor_slot_window')
    method.decorator_list = []
    scope = dict(e.scope)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), scope)
    controller = types.ModuleType('controllers.controllers')
    for name in ('normalize_day_key','parse_time_flexible','_generate_blocks','_apply_slot_rows_for_day'):
        setattr(controller, name, e.scope[name])
    monkeypatch.setitem(sys.modules, 'controllers.controllers', controller)
    with e.app.app_context():
        # An obsolete 30-minute template remains in slots for history.
        e.db.session.add(e.Slot(gaming_type_id=1,start_time=time(9),end_time=time(9,30),available_slot=3,is_available=True))
        e.db.session.commit()
        next_day = date(2026,10,12)
        scope['extend_vendor_slot_window'](1,next_day,next_day)
        rows = e.db.session.execute(text('SELECT s.start_time,s.end_time FROM vendor_1_slot v JOIN slots s ON s.id=v.slot_id WHERE v.date=:day'), {'day':next_day}).all()
        assert len(rows) == 2
        assert all(str(row.end_time).startswith(('10:00','11:00')) for row in rows)
        # Idempotent extension preserves an already reserved unit.
        e.db.session.execute(text('UPDATE vendor_1_slot SET available_slot=2 WHERE date=:day'), {'day':next_day})
        scope['extend_vendor_slot_window'](1,next_day,next_day)
        assert e.db.session.execute(text('SELECT MIN(available_slot) FROM vendor_1_slot WHERE date=:day'), {'day':next_day}).scalar() == 2


def test_save_updates_legacy_weekday_names_without_conflicting_config(setup):
    e=setup
    with e.app.app_context():
        e.db.session.execute(text("INSERT INTO vendor_day_slot_config VALUES (1,'Monday','10:00 AM','06:00 PM',30)"))
        e.db.session.execute(text("INSERT INTO vendor_day_slot_config VALUES (1,'mon','09:00 AM','05:00 PM',30)"))
        e.db.session.commit()
    response=save(e,slot_duration=60)
    assert response.status_code==200,response.json
    with e.app.app_context():
        rows=e.db.session.execute(text('SELECT opening_time,closing_time,slot_duration FROM vendor_day_slot_config WHERE vendor_id=1')).all()
        assert len(rows)==2
        assert all(row.slot_duration==60 and row.opening_time=='09:00 AM' and row.closing_time=='11:00 AM' for row in rows)
