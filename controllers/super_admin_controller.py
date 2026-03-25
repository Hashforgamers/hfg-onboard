from datetime import date
from functools import wraps
import html
import os
from typing import Optional

from flask import Blueprint, current_app, jsonify, make_response, request

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


def _promo_claim_html(ok: bool, message: str, dashboard_url: Optional[str] = None):
    title = "Subscription Enabled Successfully" if ok else "Unable to Activate Offer"
    accent = "#16a34a" if ok else "#dc2626"
    safe_message = html.escape(str(message or "").strip())
    resolved_dashboard = (dashboard_url or os.getenv("HASH_DASHBOARD_URL") or "https://dashboard.hashforgamers.com").rstrip("/")
    safe_dashboard = html.escape(resolved_dashboard)
    safe_dashboard_login = html.escape(f"{resolved_dashboard}/login")
    redirect_seconds = 4 if ok else 8
    cta_label = "Open Dashboard" if ok else "Open Dashboard Login"
    cta_url = safe_dashboard if ok else safe_dashboard_login
    button_html = ""
    helper_html = ""
    if cta_url:
        button_html = (
            f"<a href=\"{cta_url}\" style=\"display:inline-block;margin-top:16px;background:#0f172a;color:#ffffff;text-decoration:none;padding:10px 16px;border-radius:8px;font-weight:600;\">"
            f"{cta_label}"
            "</a>"
        )
    if ok:
        helper_html = (
            "<p style=\"margin:10px 0 0 0;color:#475569;font-size:13px;\">"
            "Use the login email and temporary password shared in the promotion mail, then set a new password at first login."
            "</p>"
        )
    else:
        helper_html = (
            "<p style=\"margin:10px 0 0 0;color:#475569;font-size:13px;\">"
            "If this link is expired/used, request a fresh promotion link from Hash support."
            "</p>"
        )
    page_html = f"""<!doctype html>
<html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
  </head>
  <body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="padding:28px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;">
            <tr>
              <td style="padding:20px 24px;border-bottom:1px solid #e5e7eb;background:#0b1220;color:#ffffff;">
                <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#22c55e;font-weight:700;">Hash For Gamers</div>
                <h1 style="margin:10px 0 0 0;font-size:24px;line-height:1.3;">{title}</h1>
              </td>
            </tr>
            <tr>
              <td style="padding:24px;">
                <div style="border-left:4px solid {accent};padding:10px 12px;background:#f9fafb;color:#111827;line-height:1.7;">
                  {safe_message}
                </div>
                <p style="margin:12px 0 0 0;color:#475569;font-size:13px;">
                  Redirecting to dashboard in {redirect_seconds} seconds...
                </p>
                {button_html}
                {helper_html}
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    <script>
      setTimeout(function() {{
        window.location.href = "{cta_url}";
      }}, {redirect_seconds * 1000});
    </script>
  </body>
</html>"""
    response = make_response(page_html, 200 if ok else 400)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    return response


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
    inactive_over_days = request.args.get('inactive_over_days')
    if inactive_over_days not in {None, ""}:
        try:
            inactive_over_days = max(0, int(inactive_over_days))
        except ValueError:
            return jsonify({"success": False, "message": "inactive_over_days must be an integer"}), 400
    else:
        inactive_over_days = None

    payload = SuperAdminService.list_vendors(
        page=page,
        per_page=per_page,
        status=status,
        search=search,
        verified_only=verified_only,
        subscription_state=subscription_state,
        inactive_over_days=inactive_over_days,
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
    try:
        data = request.get_json(silent=True) or {}
        new_status = (data.get('status') or '').strip().lower()
        changed_by = (data.get('changed_by') or 'super_admin').strip()

        ok, message = SuperAdminService.update_vendor_status(vendor_id, new_status, changed_by=changed_by)
        if not ok:
            return jsonify({"success": False, "message": message}), 400

        return jsonify({"success": True, "message": message}), 200
    except Exception as exc:
        current_app.logger.error("update_vendor_status failed for vendor %s: %s", vendor_id, exc, exc_info=True)
        return jsonify({"success": False, "message": f"Failed to update status: {exc}"}), 500


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


@super_admin_bp.route('/admin/subscription-models', methods=['GET'])
@require_super_admin
def list_subscription_models():
    ok, payload = SuperAdminService.list_subscription_models()
    if not ok:
        return jsonify({"success": False, "message": "Failed to fetch subscription models", "details": payload}), 400
    return jsonify({"success": True, "models": payload}), 200


@super_admin_bp.route('/admin/subscription-models', methods=['PUT'])
@require_super_admin
def update_subscription_models():
    data = request.get_json(silent=True) or {}
    models = data.get("models")
    if not isinstance(models, list) or not models:
        return jsonify({"success": False, "message": "models must be a non-empty list"}), 400

    ok, payload = SuperAdminService.update_subscription_models(models)
    if not ok:
        return jsonify({"success": False, "message": "Failed to update subscription models", "details": payload}), 400
    return jsonify({"success": True, "models": payload}), 200


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
        detail_message = ""
        if isinstance(payload, dict):
            detail_message = str(payload.get("message") or payload.get("error") or "")
        status_code = int(payload.get("_status_code", 400)) if isinstance(payload, dict) else 400
        return jsonify({
            "success": False,
            "message": detail_message or "Failed to change subscription",
            "details": payload,
        }), status_code

    return jsonify({"success": True, "vendor_id": vendor_id, "result": payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/subscriptions/provision-default', methods=['POST'])
@require_super_admin
def provision_default_subscription(vendor_id):
    ok, payload = SuperAdminService.provision_default_subscription(vendor_id)
    if not ok:
        detail_message = ""
        if isinstance(payload, dict):
            detail_message = str(payload.get("message") or payload.get("error") or "")
        status_code = int(payload.get("_status_code", 400)) if isinstance(payload, dict) else 400
        return jsonify({
            "success": False,
            "message": detail_message or "Failed to provision default subscription",
            "details": payload,
        }), status_code
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
        notify=_parse_bool(data.get("notify"), True),
    )
    if not ok:
        return jsonify({"success": False, "message": message}), 400
    return jsonify({"success": True, "message": message, "data": payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/notifications/deactivation', methods=['POST'])
@require_super_admin
def send_vendor_deactivation_notification(vendor_id):
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip() or None
    sent_by = (data.get("sent_by") or "super_admin").strip()
    ok, message, payload = SuperAdminService.send_deactivation_notice(vendor_id, reason=reason, sent_by=sent_by)
    if not ok:
        return jsonify({"success": False, "message": message}), 400
    return jsonify({"success": True, "message": message, "data": payload}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/notifications/deactivation', methods=['GET'])
@require_super_admin
def vendor_deactivation_notification_summary(vendor_id):
    summary = SuperAdminService.get_deactivation_notice_summary(vendor_id)
    return jsonify({"success": True, "vendor_id": vendor_id, "summary": summary}), 200


@super_admin_bp.route('/admin/vendors/<int:vendor_id>/notifications/promotion/early-onboard', methods=['POST'])
@require_super_admin
def send_vendor_early_onboard_promotion(vendor_id):
    data = request.get_json(silent=True) or {}
    sent_by = (data.get("sent_by") or "super_admin_dashboard").strip()
    ok, message, payload = SuperAdminService.send_early_onboard_promotion(vendor_id, sent_by=sent_by)
    if not ok:
        return jsonify({"success": False, "message": message, "details": payload}), 400
    return jsonify({"success": True, "message": message, "data": payload}), 200


@super_admin_bp.route('/promotions/early-onboard/claim', methods=['GET', 'POST'])
def claim_early_onboard_promotion():
    format_pref = (request.args.get("format") or "").strip().lower()
    # For one-click links opened in browser/email, always render an HTML landing page.
    # JSON can still be requested explicitly with ?format=json or POST API usage.
    wants_html = request.method == "GET" and format_pref != "json"

    try:
        token = (request.args.get("token") or "").strip()
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            token = token or str(data.get("token") or "").strip()
        ok, message, payload = SuperAdminService.claim_early_onboard_promotion(
            token=token,
            user_ip=request.headers.get("X-Forwarded-For") or request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
        )
        if wants_html:
            dashboard_url = payload.get("dashboard_url") if isinstance(payload, dict) else None
            return _promo_claim_html(ok, message, dashboard_url=dashboard_url)
        status_code = 200 if ok else 400
        return jsonify({"success": ok, "message": message, "data": payload or {}}), status_code
    except Exception as exc:
        current_app.logger.error("Early onboard claim route failed: %s", exc, exc_info=True)
        friendly_message = "We couldn’t activate this offer right now. Please contact Hash support."
        if wants_html:
            return _promo_claim_html(False, friendly_message)
        return jsonify({"success": False, "message": friendly_message}), 500


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
