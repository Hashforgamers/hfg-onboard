from datetime import date
from functools import wraps
import os
from typing import Optional

from flask import Blueprint, current_app, jsonify, request

from db.extensions import db
from services.super_admin_service import SuperAdminService

super_admin_bp = Blueprint('super_admin', __name__)


def _extract_admin_key():
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.headers.get("x-admin-key", "").strip()


def _parse_bool(raw, default=False):
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_date(raw: Optional[str]):
    if not raw:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).date()
    try:
        return date.fromisoformat(str(raw).strip())
    except ValueError:
        return None


def require_super_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = (os.getenv("SUPER_ADMIN_API_KEY") or "").strip()
        if not expected:
            current_app.logger.warning("SUPER_ADMIN_API_KEY not configured; allowing super-admin route in open mode")
            return fn(*args, **kwargs)

        provided = _extract_admin_key()
        if not provided or provided != expected:
            return jsonify({"success": False, "message": "Unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapper


@super_admin_bp.route('/admin/vendors', methods=['GET'])
@require_super_admin
def list_vendors():
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 20))))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid page/per_page"}), 400

    status = (request.args.get('status') or '').strip().lower()
    search = (request.args.get('search') or '').strip()
    verified_only = _parse_bool(request.args.get('verified_only'), False)
    subscription_state = (request.args.get('subscription_state') or '').strip().lower()

    payload = SuperAdminService.list_vendors(
        page=page,
        per_page=per_page,
        status=status,
        search=search,
        verified_only=verified_only,
        subscription_state=subscription_state,
    )
    return jsonify({"success": True, **payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>', methods=['GET'])
@require_super_admin
def get_vendor(vendor_id):
    payload = SuperAdminService.get_vendor_detail(vendor_id)
    if not payload:
        return jsonify({"success": False, "message": "Vendor not found"}), 404
    return jsonify({"success": True, "vendor": payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/status', methods=['POST'])
@require_super_admin
def update_vendor_status(vendor_id):
    data = request.get_json(silent=True) or {}
    new_status = (data.get('status') or '').strip().lower()
    changed_by = (data.get('changed_by') or 'super_admin').strip()

    ok, message = SuperAdminService.update_vendor_status(vendor_id, new_status, changed_by=changed_by)
    if not ok:
        return jsonify({"success": False, "message": message}), 400

    return jsonify({"success": True, "message": message}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/documents/verify', methods=['POST'])
@require_super_admin
def verify_vendor_documents(vendor_id):
    data = request.get_json(silent=True) or {}
    document_ids = data.get('document_ids') or []
    target_status = (data.get('status') or 'verified').strip().lower()

    if not isinstance(document_ids, list) or not document_ids:
        return jsonify({"success": False, "message": "document_ids must be a non-empty list"}), 400

    ok, message = SuperAdminService.verify_documents(vendor_id, document_ids, target_status)
    if not ok:
        return jsonify({"success": False, "message": message}), 400

    return jsonify({"success": True, "message": message}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/subscriptions', methods=['GET'])
@require_super_admin
def get_vendor_subscriptions(vendor_id):
    subscriptions = SuperAdminService.list_vendor_subscriptions(vendor_id)
    return jsonify({"success": True, "vendor_id": vendor_id, "subscriptions": subscriptions}), 200


@super_admin_bp.route('/admin/subscriptions', methods=['GET'])
@require_super_admin
def list_subscriptions():
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(1, int(request.args.get('per_page', 20))))
    except ValueError:
        return jsonify({"success": False, "message": "Invalid page/per_page"}), 400

    status = (request.args.get('status') or '').strip().lower()
    search = (request.args.get('search') or '').strip()
    payload = SuperAdminService.list_subscriptions(page=page, per_page=per_page, status=status, search=search)
    return jsonify({"success": True, **payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/subscriptions/change', methods=['POST'])
@require_super_admin
def change_subscription(vendor_id):
    data = request.get_json(silent=True) or {}
    package_code = (data.get("package_code") or "").strip().lower()
    immediate = _parse_bool(data.get("immediate"), True)
    unit_amount = float(data.get("unit_amount") or 0)

    if not package_code:
        return jsonify({"success": False, "message": "package_code is required"}), 400

    ok, payload = SuperAdminService.change_subscription(vendor_id, package_code, immediate=immediate, unit_amount=unit_amount)
    if not ok:
        return jsonify({"success": False, "message": "Failed to change subscription", "details": payload}), 400

    return jsonify({"success": True, "vendor_id": vendor_id, "result": payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/subscriptions/provision-default', methods=['POST'])
@require_super_admin
def provision_default_subscription(vendor_id):
    ok, payload = SuperAdminService.provision_default_subscription(vendor_id)
    if not ok:
        return jsonify({"success": False, "message": "Failed to provision default subscription", "details": payload}), 400
    return jsonify({"success": True, "vendor_id": vendor_id, "result": payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/team-access', methods=['GET'])
@require_super_admin
def get_vendor_team_access(vendor_id):
    payload = SuperAdminService.get_team_access(vendor_id)
    return jsonify({"success": True, "vendor_id": vendor_id, **payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/team-access/staff', methods=['POST'])
@require_super_admin
def create_vendor_staff(vendor_id):
    data = request.get_json(silent=True) or {}
    ok, message, staff = SuperAdminService.create_team_member(
        vendor_id=vendor_id,
        name=data.get("name"),
        role=data.get("role", "staff"),
        pin=data.get("pin"),
        is_active=_parse_bool(data.get("is_active"), True),
    )
    if not ok:
        return jsonify({"success": False, "message": message}), 400
    return jsonify({"success": True, "message": message, "staff": staff}), 201


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/team-access/staff/<int:staff_id>', methods=['PATCH'])
@require_super_admin
def update_vendor_staff(vendor_id, staff_id):
    data = request.get_json(silent=True) or {}
    ok, message, staff = SuperAdminService.update_team_member(vendor_id, staff_id, data)
    if not ok:
        return jsonify({"success": False, "message": message}), 400
    return jsonify({"success": True, "message": message, "staff": staff}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/team-access/staff/<int:staff_id>', methods=['DELETE'])
@require_super_admin
def delete_vendor_staff(vendor_id, staff_id):
    ok, message = SuperAdminService.delete_team_member(vendor_id, staff_id)
    if not ok:
        return jsonify({"success": False, "message": message}), 400
    return jsonify({"success": True, "message": message}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/team-access/role-permissions', methods=['PUT'])
@require_super_admin
def replace_vendor_role_permissions(vendor_id):
    data = request.get_json(silent=True) or {}
    role_permissions = data.get("role_permissions") or {}
    if not isinstance(role_permissions, dict):
        return jsonify({"success": False, "message": "role_permissions must be an object"}), 400

    ok, message = SuperAdminService.replace_role_permissions(vendor_id, role_permissions)
    if not ok:
        return jsonify({"success": False, "message": message}), 400

    payload = SuperAdminService.get_team_access(vendor_id)
    return jsonify({"success": True, "message": message, **payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/credentials/reset-pin', methods=['POST'])
@require_super_admin
def reset_vendor_pin(vendor_id):
    data = request.get_json(silent=True) or {}
    ok, message, payload = SuperAdminService.reset_vendor_pin(vendor_id, pin=data.get("pin"))
    if not ok:
        return jsonify({"success": False, "message": message}), 400
    return jsonify({"success": True, "message": message, "data": payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/credentials/reset-password', methods=['POST'])
@require_super_admin
def reset_vendor_password(vendor_id):
    data = request.get_json(silent=True) or {}
    ok, message, payload = SuperAdminService.reset_vendor_password(
        vendor_id,
        new_password=data.get("password"),
        notify=_parse_bool(data.get("notify"), False),
    )
    if not ok:
        return jsonify({"success": False, "message": message}), 400
    return jsonify({"success": True, "message": message, "data": payload}), 200


@super_admin_bp.route('/admin/settlements/daily', methods=['GET'])
@require_super_admin
def get_daily_settlement_summary():
    for_date = _parse_date(request.args.get("date"))
    if not for_date:
        return jsonify({"success": False, "message": "date must be YYYY-MM-DD"}), 400

    vendor_raw = request.args.get("vendor_id")
    vendor_id = int(vendor_raw) if vendor_raw and str(vendor_raw).isdigit() else None

    payload = SuperAdminService.get_settlement_summary(settlement_date=for_date, vendor_id=vendor_id)
    return jsonify({"success": True, **payload}), 200


@super_admin_bp.route('/admin/settlements/daily/settle', methods=['POST'])
@require_super_admin
def settle_vendor_daily():
    data = request.get_json(silent=True) or {}
    vendor_id = data.get("vendor_id")
    if vendor_id is None:
        return jsonify({"success": False, "message": "vendor_id is required"}), 400
    try:
        vendor_id = int(vendor_id)
    except Exception:
        return jsonify({"success": False, "message": "vendor_id must be integer"}), 400

    for_date = _parse_date(data.get("date"))
    if not for_date:
        return jsonify({"success": False, "message": "date must be YYYY-MM-DD"}), 400

    actor = str(data.get("actor") or "super_admin").strip()
    payload = SuperAdminService.settle_vendor_day(vendor_id=vendor_id, settlement_date=for_date, actor=actor)
    return jsonify({"success": True, "result": payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>', methods=['DELETE'])
@require_super_admin
def deboard_vendor_admin(vendor_id):
    """Super-admin friendly deboard route (transaction wrapped)."""
    try:
        from services.services import VendorService

        VendorService.deboard_vendor(vendor_id)
        db.session.commit()
        return jsonify({"success": True, "message": f"Vendor {vendor_id} deboarded successfully"}), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"Failed to deboard vendor {vendor_id}: {exc}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to deboard vendor", "error": str(exc)}), 500
