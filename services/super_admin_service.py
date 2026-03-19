import os
import random
import string
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional, Dict, List

import requests
from flask import current_app
from flask_mail import Message
from sqlalchemy import and_, bindparam, case, func, inspect, or_, text
from werkzeug.security import generate_password_hash

from db.extensions import db, mail
from models.contactInfo import ContactInfo
from models.document import Document
from models.passwordManager import PasswordManager
from models.physicalAddress import PhysicalAddress
from models.transaction import Transaction
from models.vendor import Vendor
from models.vendorPin import VendorPin
from models.vendorStatus import VendorStatus


class SuperAdminService:
    ALLOWED_STATUSES = {
        "pending_verification",
        "active",
        "inactive",
        "rejected",
        "suspended",
    }

    APP_PAYMENT_MODES = {
        "payment_gateway",
        "upi",
        "debit_card",
        "credit_card",
        "wallet",
        "online",
        "app",
        "razorpay",
        "netbanking",
    }

    PENDING_SETTLEMENT_STATES = {"", "pending", "unpaid", "due"}
    COMPLETE_SETTLEMENT_STATES = {"processed", "completed", "paid", "settled"}

    _table_cache: Dict[str, bool] = {}

    @staticmethod
    def _dashboard_service_url() -> str:
        return (os.getenv("DASHBOARD_SERVICE_URL") or "https://hfg-dashboard.onrender.com").rstrip("/")

    @staticmethod
    def _admin_proxy_headers() -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        admin_key = (os.getenv("SUPER_ADMIN_API_KEY") or "").strip()
        if admin_key:
            headers["x-admin-key"] = admin_key
        return headers

    @staticmethod
    def _ensure_deactivation_notice_table():
        if SuperAdminService._has_table("vendor_deactivation_notifications"):
            return
        try:
            db.session.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS vendor_deactivation_notifications (
                      id BIGSERIAL PRIMARY KEY,
                      vendor_id INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
                      sent_to_email VARCHAR(255),
                      reason TEXT,
                      loss_summary TEXT,
                      sent_by VARCHAR(128) DEFAULT 'super_admin',
                      sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            db.session.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_vendor_deactivation_notice_vendor_sent
                    ON vendor_deactivation_notifications (vendor_id, sent_at DESC)
                    """
                )
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
        SuperAdminService._table_cache["vendor_deactivation_notifications"] = True

    @staticmethod
    def _deactivation_notice_summary_map(vendor_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        if not vendor_ids:
            return {}
        SuperAdminService._ensure_deactivation_notice_table()
        if not SuperAdminService._has_table("vendor_deactivation_notifications"):
            return {}

        sql = text(
            """
            SELECT vendor_id,
                   COUNT(*) AS sent_count,
                   MAX(sent_at) AS last_sent_at
            FROM vendor_deactivation_notifications
            WHERE vendor_id IN :vendor_ids
            GROUP BY vendor_id
            """
        ).bindparams(bindparam("vendor_ids", expanding=True))
        rows = db.session.execute(sql, {"vendor_ids": vendor_ids}).mappings().all()
        out: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            out[int(row["vendor_id"])] = {
                "sent_count": int(row["sent_count"] or 0),
                "last_sent_at": row["last_sent_at"],
            }
        return out

    @staticmethod
    def _has_table(table_name: str) -> bool:
        if table_name in SuperAdminService._table_cache:
            return SuperAdminService._table_cache[table_name]
        try:
            exists = inspect(db.engine).has_table(table_name)
        except Exception:
            exists = False
        SuperAdminService._table_cache[table_name] = bool(exists)
        return bool(exists)

    @staticmethod
    def _latest_status_subquery():
        latest_ts = (
            db.session.query(
                VendorStatus.vendor_id.label("vendor_id"),
                func.max(VendorStatus.updated_at).label("updated_at"),
            )
            .group_by(VendorStatus.vendor_id)
            .subquery()
        )
        latest_status = (
            db.session.query(
                VendorStatus.vendor_id.label("vendor_id"),
                VendorStatus.status.label("status"),
                VendorStatus.updated_at.label("status_updated_at"),
            )
            .join(
                latest_ts,
                and_(
                    latest_ts.c.vendor_id == VendorStatus.vendor_id,
                    latest_ts.c.updated_at == VendorStatus.updated_at,
                ),
            )
            .subquery()
        )
        return latest_status

    @staticmethod
    def _normalize_bool(value: Any, default: bool = False) -> bool:
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _mask_secret(value: Optional[str], keep: int = 2) -> Optional[str]:
        if not value:
            return None
        raw = str(value)
        if len(raw) <= keep:
            return "*" * len(raw)
        return ("*" * (len(raw) - keep)) + raw[-keep:]

    @staticmethod
    def _parse_iso_date(raw: Optional[str]) -> date:
        if not raw:
            return datetime.now(timezone.utc).date()
        try:
            return date.fromisoformat(str(raw).strip())
        except ValueError:
            raise ValueError("date must be in YYYY-MM-DD format")

    @staticmethod
    def _generate_password(length: int = 10) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(random.choice(alphabet) for _ in range(length))

    @staticmethod
    def _generate_pin() -> str:
        while True:
            pin = f"{random.randint(0, 9999):04d}"
            if not VendorPin.query.filter_by(pin_code=pin).first():
                return pin

    @staticmethod
    def _subscription_snapshot_map(vendor_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        if not vendor_ids or not SuperAdminService._has_table("subscriptions"):
            return {}

        sql = text(
            """
            SELECT vendor_id,
                   status,
                   package_id,
                   package_code,
                   package_name,
                   pc_limit,
                   unit_amount,
                   current_period_start,
                   current_period_end,
                   created_at
            FROM (
                SELECT s.vendor_id,
                       s.status,
                       s.package_id,
                       p.code AS package_code,
                       p.name AS package_name,
                       p.pc_limit,
                       s.unit_amount,
                       s.current_period_start,
                       s.current_period_end,
                       s.created_at,
                       ROW_NUMBER() OVER (
                         PARTITION BY s.vendor_id
                         ORDER BY s.created_at DESC, s.id DESC
                       ) AS rn
                FROM subscriptions s
                LEFT JOIN packages p ON p.id = s.package_id
                WHERE s.vendor_id IN :vendor_ids
            ) latest
            WHERE rn = 1
            """
        ).bindparams(bindparam("vendor_ids", expanding=True))

        now_utc = datetime.now(timezone.utc)
        rows = db.session.execute(sql, {"vendor_ids": vendor_ids}).mappings().all()
        result: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            end_dt = row["current_period_end"]
            if end_dt and getattr(end_dt, "tzinfo", None) is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            status = str(row["status"] or "").lower()
            is_active = status in {"active", "trialing", "past_due"} and (end_dt is None or end_dt >= now_utc)
            inactive_for_days = None
            if not is_active and end_dt is not None:
                inactive_for_days = max((now_utc.date() - end_dt.date()).days, 0)
            result[int(row["vendor_id"])] = {
                "status": status or "none",
                "is_active": bool(is_active),
                "inactive_for_days": inactive_for_days,
                "inactive_over_90_days": bool((inactive_for_days or 0) >= 90),
                "package": {
                    "id": row["package_id"],
                    "code": row["package_code"],
                    "name": row["package_name"],
                    "pc_limit": row["pc_limit"],
                },
                "amount_paid": float(row["unit_amount"] or 0),
                "period_start": row["current_period_start"],
                "period_end": row["current_period_end"],
                "created_at": row["created_at"],
            }
        return result

    @staticmethod
    def _vendor_pin_map(vendor_ids: List[int]) -> Dict[int, str]:
        if not vendor_ids:
            return {}
        rows = VendorPin.query.filter(VendorPin.vendor_id.in_(vendor_ids)).all()
        return {int(row.vendor_id): str(row.pin_code) for row in rows if row.pin_code}

    @staticmethod
    def _password_snapshot_map(vendor_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        if not vendor_ids:
            return {}
        rows = (
            PasswordManager.query
            .filter(
                PasswordManager.parent_type == "vendor",
                PasswordManager.parent_id.in_(vendor_ids),
            )
            .all()
        )
        mapped: Dict[int, Dict[str, Any]] = {}
        for row in rows:
            vid = int(row.parent_id)
            raw = row.password or ""
            is_hashed = raw.startswith("pbkdf2:") or raw.startswith("scrypt:")
            mapped[vid] = {
                "has_password": bool(raw),
                "is_hashed": bool(is_hashed),
                "masked_preview": None if is_hashed else SuperAdminService._mask_secret(raw, keep=2),
                "credential_userid": str(row.userid) if row.userid is not None else None,
            }
        return mapped

    @staticmethod
    def _team_snapshot_map(vendor_ids: List[int]) -> Dict[int, Dict[str, int]]:
        if not vendor_ids or not SuperAdminService._has_table("vendor_staff"):
            return {}

        sql = text(
            """
            SELECT vendor_id,
                   COUNT(*) AS total_count,
                   SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS active_count
            FROM vendor_staff
            WHERE vendor_id IN :vendor_ids
            GROUP BY vendor_id
            """
        ).bindparams(bindparam("vendor_ids", expanding=True))

        rows = db.session.execute(sql, {"vendor_ids": vendor_ids}).mappings().all()
        mapped: Dict[int, Dict[str, int]] = {}
        for row in rows:
            mapped[int(row["vendor_id"])] = {
                "total": int(row["total_count"] or 0),
                "active": int(row["active_count"] or 0),
            }
        return mapped

    @staticmethod
    def list_vendors(
        page=1,
        per_page=20,
        status=None,
        search=None,
        verified_only=False,
        subscription_state=None,
        inactive_over_days: Optional[int] = None,
    ):
        latest_status = SuperAdminService._latest_status_subquery()

        total_docs_subq = (
            db.session.query(func.count(Document.id))
            .filter(Document.vendor_id == Vendor.id)
            .correlate(Vendor)
            .scalar_subquery()
        )
        verified_docs_subq = (
            db.session.query(func.count(Document.id))
            .filter(Document.vendor_id == Vendor.id, Document.status == "verified")
            .correlate(Vendor)
            .scalar_subquery()
        )

        query = (
            db.session.query(
                Vendor.id.label("vendor_id"),
                Vendor.cafe_name,
                Vendor.owner_name,
                Vendor.account_id,
                Vendor.created_at,
                Vendor.updated_at,
                latest_status.c.status,
                latest_status.c.status_updated_at,
                ContactInfo.email,
                ContactInfo.phone,
                PhysicalAddress.addressLine1,
                PhysicalAddress.addressLine2,
                PhysicalAddress.state,
                PhysicalAddress.pincode,
                PhysicalAddress.country,
                PhysicalAddress.latitude,
                PhysicalAddress.longitude,
                total_docs_subq.label("total_documents"),
                verified_docs_subq.label("verified_documents"),
            )
            .outerjoin(latest_status, latest_status.c.vendor_id == Vendor.id)
            .outerjoin(
                ContactInfo,
                and_(ContactInfo.parent_id == Vendor.id, ContactInfo.parent_type == "vendor"),
            )
            .outerjoin(
                PhysicalAddress,
                and_(
                    PhysicalAddress.parent_id == Vendor.id,
                    PhysicalAddress.parent_type == "vendor",
                    PhysicalAddress.is_active.is_(True),
                ),
            )
        )

        if status:
            query = query.filter(func.lower(func.coalesce(latest_status.c.status, "")) == status.lower())

        if verified_only:
            query = query.filter(verified_docs_subq == total_docs_subq, total_docs_subq > 0)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Vendor.cafe_name.ilike(pattern),
                    Vendor.owner_name.ilike(pattern),
                    ContactInfo.email.ilike(pattern),
                    ContactInfo.phone.ilike(pattern),
                )
            )

        total = query.count()
        rows = (
            query.order_by(Vendor.created_at.desc(), Vendor.id.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )

        vendor_ids = [int(row.vendor_id) for row in rows]
        subscription_map = SuperAdminService._subscription_snapshot_map(vendor_ids)
        pin_map = SuperAdminService._vendor_pin_map(vendor_ids)
        password_map = SuperAdminService._password_snapshot_map(vendor_ids)
        team_map = SuperAdminService._team_snapshot_map(vendor_ids)
        notice_map = SuperAdminService._deactivation_notice_summary_map(vendor_ids)

        vendors = []
        for row in rows:
            sub = subscription_map.get(int(row.vendor_id))
            if subscription_state:
                requested = str(subscription_state).strip().lower()
                is_active = bool((sub or {}).get("is_active", False))
                if requested == "active" and not is_active:
                    continue
                if requested == "inactive" and is_active:
                    continue
            if inactive_over_days is not None:
                days_inactive = int((sub or {}).get("inactive_for_days") or 0)
                if days_inactive < int(inactive_over_days):
                    continue

            total_docs = int(row.total_documents or 0)
            verified_docs = int(row.verified_documents or 0)
            raw_status = str(row.status or "pending_verification")
            effective_status = raw_status
            if raw_status in {"active", "inactive"}:
                effective_status = "active" if bool((sub or {}).get("is_active", False)) else "inactive"

            vendors.append(
                {
                    "vendor_id": row.vendor_id,
                    "cafe_name": row.cafe_name,
                    "owner_name": row.owner_name,
                    "account_id": row.account_id,
                    "status": effective_status,
                    "raw_status": raw_status,
                    "status_updated_at": row.status_updated_at,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                    "email": row.email,
                    "phone": row.phone,
                    "address": {
                        "addressLine1": row.addressLine1,
                        "addressLine2": row.addressLine2,
                        "state": row.state,
                        "pincode": row.pincode,
                        "country": row.country,
                        "latitude": row.latitude,
                        "longitude": row.longitude,
                    },
                    "documents": {
                        "total": total_docs,
                        "verified": verified_docs,
                        "pending": max(total_docs - verified_docs, 0),
                        "is_fully_verified": total_docs > 0 and verified_docs == total_docs,
                    },
                    "subscription": sub
                    or {
                        "status": "none",
                        "is_active": False,
                        "inactive_for_days": None,
                        "inactive_over_90_days": False,
                        "package": None,
                        "amount_paid": 0,
                        "period_start": None,
                        "period_end": None,
                        "created_at": None,
                    },
                    "credentials": {
                        "pin": pin_map.get(int(row.vendor_id)),
                        "password": password_map.get(int(row.vendor_id), {
                            "has_password": False,
                            "is_hashed": False,
                            "masked_preview": None,
                            "credential_userid": None,
                        }),
                    },
                    "team_access": team_map.get(int(row.vendor_id), {"total": 0, "active": 0}),
                    "deactivation_notifications": notice_map.get(int(row.vendor_id), {"sent_count": 0, "last_sent_at": None}),
                }
            )

        return {
            "vendors": vendors,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page if per_page else 1,
            },
        }

    @staticmethod
    def list_vendor_subscriptions(vendor_id: int):
        if not SuperAdminService._has_table("subscriptions"):
            return []

        sql = text(
            """
            SELECT s.id,
                   s.vendor_id,
                   s.status,
                   s.package_id,
                   p.code AS package_code,
                   p.name AS package_name,
                   p.pc_limit,
                   s.current_period_start,
                   s.current_period_end,
                   s.unit_amount,
                   s.currency,
                   s.external_ref,
                   s.created_at,
                   s.updated_at
            FROM subscriptions s
            LEFT JOIN packages p ON p.id = s.package_id
            WHERE s.vendor_id = :vendor_id
            ORDER BY s.created_at DESC, s.id DESC
            """
        )
        rows = db.session.execute(sql, {"vendor_id": vendor_id}).mappings().all()
        data = []
        for row in rows:
            data.append(
                {
                    "id": row["id"],
                    "vendor_id": row["vendor_id"],
                    "status": str(row["status"] or ""),
                    "package": {
                        "id": row["package_id"],
                        "code": row["package_code"],
                        "name": row["package_name"],
                        "pc_limit": row["pc_limit"],
                    },
                    "period_start": row["current_period_start"],
                    "period_end": row["current_period_end"],
                    "amount_paid": float(row["unit_amount"] or 0),
                    "currency": row["currency"],
                    "external_ref": row["external_ref"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
        return data

    @staticmethod
    def list_subscriptions(page=1, per_page=20, status=None, search=None):
        if not SuperAdminService._has_table("subscriptions"):
            return {
                "subscriptions": [],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": 0,
                    "total_pages": 0,
                },
            }

        base_sql = (
            " FROM subscriptions s"
            " LEFT JOIN packages p ON p.id = s.package_id"
            " LEFT JOIN vendors v ON v.id = s.vendor_id"
            " WHERE 1=1"
        )
        params: dict[str, Any] = {}

        if status:
            base_sql += " AND lower(cast(s.status as text)) = :status"
            params["status"] = str(status).strip().lower()

        if search:
            base_sql += (
                " AND ("
                "v.cafe_name ILIKE :search OR v.owner_name ILIKE :search OR "
                "cast(v.id as text) ILIKE :search OR p.name ILIKE :search"
                ")"
            )
            params["search"] = f"%{search.strip()}%"

        count_sql = text("SELECT COUNT(*)" + base_sql)
        total = int(db.session.execute(count_sql, params).scalar() or 0)

        list_sql = text(
            """
            SELECT s.id,
                   s.vendor_id,
                   v.cafe_name,
                   v.owner_name,
                   s.status,
                   p.code AS package_code,
                   p.name AS package_name,
                   p.pc_limit,
                   s.current_period_start,
                   s.current_period_end,
                   s.unit_amount,
                   s.currency,
                   s.external_ref,
                   s.created_at
            """
            + base_sql
            + " ORDER BY s.created_at DESC, s.id DESC LIMIT :limit OFFSET :offset"
        )
        params.update({"limit": per_page, "offset": (page - 1) * per_page})

        rows = db.session.execute(list_sql, params).mappings().all()
        items = []
        for row in rows:
            items.append(
                {
                    "id": row["id"],
                    "vendor_id": row["vendor_id"],
                    "cafe_name": row["cafe_name"],
                    "owner_name": row["owner_name"],
                    "status": str(row["status"] or ""),
                    "package": {
                        "code": row["package_code"],
                        "name": row["package_name"],
                        "pc_limit": row["pc_limit"],
                    },
                    "period_start": row["current_period_start"],
                    "period_end": row["current_period_end"],
                    "amount_paid": float(row["unit_amount"] or 0),
                    "currency": row["currency"],
                    "external_ref": row["external_ref"],
                    "created_at": row["created_at"],
                }
            )

        return {
            "subscriptions": items,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page if per_page else 1,
            },
        }

    @staticmethod
    def get_team_access(vendor_id: int):
        if not SuperAdminService._has_table("vendor_staff"):
            return {"staff": [], "role_permissions": {}, "available": False}

        staff_sql = text(
            """
            SELECT id, vendor_id, name, role, pin_code, is_active, created_at, updated_at
            FROM vendor_staff
            WHERE vendor_id = :vendor_id
            ORDER BY created_at ASC, id ASC
            """
        )
        staff_rows = db.session.execute(staff_sql, {"vendor_id": vendor_id}).mappings().all()
        staff = [
            {
                "id": r["id"],
                "vendor_id": r["vendor_id"],
                "name": r["name"],
                "role": r["role"],
                "pin_code": r["pin_code"],
                "is_active": bool(r["is_active"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in staff_rows
        ]

        role_permissions: dict[str, list[str]] = {}
        if SuperAdminService._has_table("vendor_role_permissions"):
            perm_sql = text(
                """
                SELECT role, permission
                FROM vendor_role_permissions
                WHERE vendor_id = :vendor_id
                ORDER BY role ASC, permission ASC
                """
            )
            perm_rows = db.session.execute(perm_sql, {"vendor_id": vendor_id}).mappings().all()
            for row in perm_rows:
                role = str(row["role"])
                role_permissions.setdefault(role, []).append(str(row["permission"]))

        return {
            "available": True,
            "staff": staff,
            "role_permissions": role_permissions,
        }

    @staticmethod
    def create_team_member(vendor_id: int, name: str, role: str, pin: Optional[str] = None, is_active: bool = True):
        if not SuperAdminService._has_table("vendor_staff"):
            return False, "Team access table not available", None

        role = (role or "staff").strip().lower()
        if role not in {"owner", "manager", "staff"}:
            return False, "role must be one of owner/manager/staff", None

        clean_name = (name or "").strip()
        if not clean_name:
            return False, "name is required", None

        if pin is None or str(pin).strip() == "":
            pin = f"{random.randint(0, 9999):04d}"
        pin = str(pin).strip()
        if not pin.isdigit() or len(pin) != 4:
            return False, "pin must be exactly 4 digits", None

        insert_sql = text(
            """
            INSERT INTO vendor_staff (vendor_id, name, role, pin_code, pin_hash, is_active, created_at, updated_at)
            VALUES (:vendor_id, :name, :role, :pin_code, :pin_hash, :is_active, now(), now())
            RETURNING id, vendor_id, name, role, pin_code, is_active, created_at, updated_at
            """
        )

        try:
            row = db.session.execute(
                insert_sql,
                {
                    "vendor_id": vendor_id,
                    "name": clean_name,
                    "role": role,
                    "pin_code": pin,
                    "pin_hash": generate_password_hash(pin),
                    "is_active": bool(is_active),
                },
            ).mappings().first()
            db.session.commit()
            payload = {
                "id": row["id"],
                "vendor_id": row["vendor_id"],
                "name": row["name"],
                "role": row["role"],
                "pin_code": row["pin_code"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            return True, "Staff created", payload
        except Exception as exc:
            db.session.rollback()
            return False, str(exc), None

    @staticmethod
    def update_team_member(vendor_id: int, staff_id: int, payload: dict[str, Any]):
        if not SuperAdminService._has_table("vendor_staff"):
            return False, "Team access table not available", None

        allowed_fields = {"name", "role", "is_active", "pin"}
        updates = {k: v for k, v in (payload or {}).items() if k in allowed_fields}
        if not updates:
            return False, "No valid fields to update", None

        set_parts = []
        params: dict[str, Any] = {"vendor_id": vendor_id, "staff_id": staff_id}

        if "name" in updates:
            name = str(updates["name"] or "").strip()
            if not name:
                return False, "name cannot be empty", None
            set_parts.append("name = :name")
            params["name"] = name

        if "role" in updates:
            role = str(updates["role"] or "").strip().lower()
            if role not in {"owner", "manager", "staff"}:
                return False, "role must be one of owner/manager/staff", None
            set_parts.append("role = :role")
            params["role"] = role

        if "is_active" in updates:
            set_parts.append("is_active = :is_active")
            params["is_active"] = bool(updates["is_active"])

        if "pin" in updates:
            pin = str(updates["pin"] or "").strip()
            if not pin.isdigit() or len(pin) != 4:
                return False, "pin must be exactly 4 digits", None
            set_parts.append("pin_code = :pin_code")
            set_parts.append("pin_hash = :pin_hash")
            params["pin_code"] = pin
            params["pin_hash"] = generate_password_hash(pin)

        update_sql = text(
            f"""
            UPDATE vendor_staff
            SET {', '.join(set_parts)}, updated_at = now()
            WHERE id = :staff_id AND vendor_id = :vendor_id
            RETURNING id, vendor_id, name, role, pin_code, is_active, created_at, updated_at
            """
        )

        try:
            row = db.session.execute(update_sql, params).mappings().first()
            if not row:
                db.session.rollback()
                return False, "Staff member not found", None
            db.session.commit()
            payload = {
                "id": row["id"],
                "vendor_id": row["vendor_id"],
                "name": row["name"],
                "role": row["role"],
                "pin_code": row["pin_code"],
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            return True, "Staff updated", payload
        except Exception as exc:
            db.session.rollback()
            return False, str(exc), None

    @staticmethod
    def delete_team_member(vendor_id: int, staff_id: int):
        if not SuperAdminService._has_table("vendor_staff"):
            return False, "Team access table not available"

        delete_sql = text(
            "DELETE FROM vendor_staff WHERE id = :staff_id AND vendor_id = :vendor_id"
        )
        result = db.session.execute(delete_sql, {"staff_id": staff_id, "vendor_id": vendor_id})
        if int(result.rowcount or 0) <= 0:
            db.session.rollback()
            return False, "Staff member not found"

        db.session.commit()
        return True, "Staff deleted"

    @staticmethod
    def replace_role_permissions(vendor_id: int, role_permissions: Dict[str, List[str]]):
        if not SuperAdminService._has_table("vendor_role_permissions"):
            return False, "Role permissions table not available"

        try:
            db.session.execute(
                text("DELETE FROM vendor_role_permissions WHERE vendor_id = :vendor_id"),
                {"vendor_id": vendor_id},
            )

            for role, permissions in (role_permissions or {}).items():
                clean_role = str(role or "").strip().lower()
                if clean_role not in {"owner", "manager", "staff"}:
                    continue
                for permission in permissions or []:
                    perm = str(permission or "").strip()
                    if not perm:
                        continue
                    db.session.execute(
                        text(
                            """
                            INSERT INTO vendor_role_permissions (vendor_id, role, permission)
                            VALUES (:vendor_id, :role, :permission)
                            """
                        ),
                        {
                            "vendor_id": vendor_id,
                            "role": clean_role,
                            "permission": perm,
                        },
                    )

            db.session.commit()
            return True, "Role permissions updated"
        except Exception as exc:
            db.session.rollback()
            return False, str(exc)

    @staticmethod
    def get_vendor_detail(vendor_id):
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return None

        latest_status = (
            VendorStatus.query.filter_by(vendor_id=vendor_id)
            .order_by(VendorStatus.updated_at.desc(), VendorStatus.id.desc())
            .first()
        )
        contact = ContactInfo.query.filter_by(parent_id=vendor_id, parent_type="vendor").first()
        address = (
            PhysicalAddress.query.filter_by(parent_id=vendor_id, parent_type="vendor", is_active=True)
            .order_by(PhysicalAddress.id.desc())
            .first()
        )
        docs = Document.query.filter_by(vendor_id=vendor_id).order_by(Document.uploaded_at.desc(), Document.id.desc()).all()

        pin = VendorPin.query.filter_by(vendor_id=vendor_id).first()
        password_row = PasswordManager.query.filter_by(parent_type="vendor", parent_id=vendor_id).first()
        password_val = (password_row.password or "") if password_row else ""
        is_hashed = password_val.startswith("pbkdf2:") or password_val.startswith("scrypt:")

        team_access = SuperAdminService.get_team_access(vendor_id)
        subscriptions = SuperAdminService.list_vendor_subscriptions(vendor_id)

        return {
            "vendor_id": vendor.id,
            "cafe_name": vendor.cafe_name,
            "owner_name": vendor.owner_name,
            "description": vendor.description,
            "account_id": vendor.account_id,
            "account_email": vendor.account.email if vendor.account else None,
            "contact": {
                "email": contact.email if contact else None,
                "phone": contact.phone if contact else None,
            },
            "address": {
                "addressLine1": address.addressLine1 if address else None,
                "addressLine2": address.addressLine2 if address else None,
                "state": address.state if address else None,
                "pincode": address.pincode if address else None,
                "country": address.country if address else None,
                "latitude": address.latitude if address else None,
                "longitude": address.longitude if address else None,
            },
            "status": latest_status.status if latest_status else "pending_verification",
            "status_updated_at": latest_status.updated_at if latest_status else None,
            "documents": [
                {
                    "id": doc.id,
                    "document_type": doc.document_type,
                    "document_url": doc.document_url,
                    "status": doc.status,
                    "uploaded_at": doc.uploaded_at,
                }
                for doc in docs
            ],
            "credentials": {
                "vendor_pin": pin.pin_code if pin else None,
                "password": {
                    "has_password": bool(password_val),
                    "is_hashed": bool(is_hashed),
                    "masked_preview": None if is_hashed else SuperAdminService._mask_secret(password_val, keep=2),
                    "credential_userid": str(password_row.userid) if password_row else None,
                },
            },
            "team_access": team_access,
            "subscriptions": subscriptions,
            "created_at": vendor.created_at,
            "updated_at": vendor.updated_at,
        }

    @staticmethod
    def update_vendor_status(vendor_id, new_status, changed_by="super_admin"):
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return False, "Vendor not found"

        if new_status not in SuperAdminService.ALLOWED_STATUSES:
            return False, f"Invalid status. Allowed: {', '.join(sorted(SuperAdminService.ALLOWED_STATUSES))}"

        status_row = VendorStatus(vendor_id=vendor_id, status=new_status, updated_at=datetime.utcnow())
        db.session.add(status_row)
        db.session.commit()

        return True, f"Vendor status updated to '{new_status}' by {changed_by}"

    @staticmethod
    def verify_documents(vendor_id, document_ids, target_status="verified"):
        if target_status not in {"verified", "unverified", "rejected"}:
            return False, "status must be one of verified/unverified/rejected"

        docs = (
            Document.query.filter(Document.vendor_id == vendor_id, Document.id.in_(document_ids)).all()
        )
        if not docs:
            return False, "No matching vendor documents found"

        for doc in docs:
            doc.status = target_status

        pending_count = Document.query.filter(
            Document.vendor_id == vendor_id,
            Document.status != "verified",
        ).count()

        next_status = "active" if pending_count == 0 else "pending_verification"
        db.session.add(VendorStatus(vendor_id=vendor_id, status=next_status, updated_at=datetime.utcnow()))
        db.session.commit()

        return True, f"Updated {len(docs)} documents to '{target_status}'. Vendor status -> {next_status}."

    @staticmethod
    def get_settlement_summary(settlement_date: date, vendor_id: Optional[int] = None):
        mode_norm = func.lower(func.coalesce(Transaction.mode_of_payment, ""))
        settlement_norm = func.lower(func.coalesce(Transaction.settlement_status, ""))
        day_col = func.coalesce(Transaction.booking_date, Transaction.booked_date)

        app_amount_case = case(
            (mode_norm.in_(tuple(SuperAdminService.APP_PAYMENT_MODES)), Transaction.amount),
            else_=0.0,
        )
        due_amount_case = case(
            (
                and_(
                    mode_norm.in_(tuple(SuperAdminService.APP_PAYMENT_MODES)),
                    settlement_norm.in_(tuple(SuperAdminService.PENDING_SETTLEMENT_STATES)),
                ),
                Transaction.amount,
            ),
            else_=0.0,
        )
        settled_amount_case = case(
            (
                and_(
                    mode_norm.in_(tuple(SuperAdminService.APP_PAYMENT_MODES)),
                    settlement_norm.in_(tuple(SuperAdminService.COMPLETE_SETTLEMENT_STATES)),
                ),
                Transaction.amount,
            ),
            else_=0.0,
        )

        query = (
            db.session.query(
                Transaction.vendor_id.label("vendor_id"),
                Vendor.cafe_name.label("cafe_name"),
                func.count(func.distinct(Transaction.booking_id)).label("booking_count"),
                func.count(Transaction.id).label("transaction_count"),
                func.sum(app_amount_case).label("app_collected"),
                func.sum(due_amount_case).label("pending_settlement"),
                func.sum(settled_amount_case).label("settled_amount"),
            )
            .outerjoin(Vendor, Vendor.id == Transaction.vendor_id)
            .filter(Transaction.vendor_id.isnot(None), day_col == settlement_date)
            .group_by(Transaction.vendor_id, Vendor.cafe_name)
            .order_by(Vendor.cafe_name.asc())
        )

        if vendor_id is not None:
            query = query.filter(Transaction.vendor_id == int(vendor_id))

        rows = query.all()
        items = []
        total_due = 0.0
        total_collected = 0.0
        total_settled = 0.0
        for row in rows:
            app_collected = float(row.app_collected or 0)
            pending_settlement = float(row.pending_settlement or 0)
            settled_amount = float(row.settled_amount or 0)
            total_collected += app_collected
            total_due += pending_settlement
            total_settled += settled_amount
            items.append(
                {
                    "vendor_id": int(row.vendor_id),
                    "cafe_name": row.cafe_name,
                    "booking_count": int(row.booking_count or 0),
                    "transaction_count": int(row.transaction_count or 0),
                    "app_collected": round(app_collected, 2),
                    "pending_settlement": round(pending_settlement, 2),
                    "already_settled": round(settled_amount, 2),
                }
            )

        return {
            "date": settlement_date.isoformat(),
            "summary": {
                "vendors": len(items),
                "total_app_collected": round(total_collected, 2),
                "total_pending_settlement": round(total_due, 2),
                "total_already_settled": round(total_settled, 2),
            },
            "rows": items,
        }

    @staticmethod
    def settle_vendor_day(vendor_id: int, settlement_date: date, actor: str = "super_admin"):
        mode_norm = func.lower(func.coalesce(Transaction.mode_of_payment, ""))
        settlement_norm = func.lower(func.coalesce(Transaction.settlement_status, ""))
        day_col = func.coalesce(Transaction.booking_date, Transaction.booked_date)

        tx_rows = (
            Transaction.query.filter(
                Transaction.vendor_id == int(vendor_id),
                day_col == settlement_date,
                mode_norm.in_(tuple(SuperAdminService.APP_PAYMENT_MODES)),
                settlement_norm.in_(tuple(SuperAdminService.PENDING_SETTLEMENT_STATES)),
            )
            .order_by(Transaction.id.asc())
            .all()
        )

        if not tx_rows:
            return {
                "vendor_id": int(vendor_id),
                "date": settlement_date.isoformat(),
                "updated_count": 0,
                "settled_amount": 0.0,
                "message": "No pending app-paid transactions found for settlement.",
            }

        settled_amount = 0.0
        for tx in tx_rows:
            settled_amount += float(tx.amount or 0)
            tx.settlement_status = "processed"
            tx.updated_at = datetime.utcnow()

        db.session.commit()
        return {
            "vendor_id": int(vendor_id),
            "date": settlement_date.isoformat(),
            "updated_count": len(tx_rows),
            "settled_amount": round(settled_amount, 2),
            "updated_by": actor,
        }

    @staticmethod
    def reset_vendor_pin(vendor_id: int, pin: Optional[str] = None):
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return False, "Vendor not found", None

        if pin is None or str(pin).strip() == "":
            pin = SuperAdminService._generate_pin()
        pin = str(pin).strip()
        if not pin.isdigit() or len(pin) != 4:
            return False, "pin must be exactly 4 digits", None

        conflict = VendorPin.query.filter(VendorPin.pin_code == pin, VendorPin.vendor_id != vendor_id).first()
        if conflict:
            return False, "pin already in use", None

        vendor_pin = VendorPin.query.filter_by(vendor_id=vendor_id).first()
        if not vendor_pin:
            vendor_pin = VendorPin(vendor_id=vendor_id, pin_code=pin)
            db.session.add(vendor_pin)
        else:
            vendor_pin.pin_code = pin

        db.session.commit()
        return True, "PIN updated", {"vendor_id": vendor_id, "pin_code": pin}

    @staticmethod
    def reset_vendor_password(vendor_id: int, new_password: Optional[str] = None, notify: bool = False):
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return False, "Vendor not found", None

        password = (new_password or "").strip() or SuperAdminService._generate_password()
        if len(password) < 6:
            return False, "password must be at least 6 characters", None

        vendor_ids_scope = [vendor_id]
        if vendor.account_id:
            vendor_ids_scope = [
                int(v.id)
                for v in Vendor.query.filter(Vendor.account_id == vendor.account_id).with_entities(Vendor.id).all()
            ] or [vendor_id]

        existing_rows = (
            PasswordManager.query
            .filter(
                PasswordManager.parent_type == "vendor",
                PasswordManager.parent_id.in_(vendor_ids_scope),
            )
            .all()
        )

        if not existing_rows:
            existing_rows = [
                PasswordManager(
                    userid=str(vendor_id),
                    password=password,
                    parent_id=vendor_id,
                    parent_type="vendor",
                )
            ]
            db.session.add_all(existing_rows)
        else:
            for row in existing_rows:
                row.password = password

        db.session.commit()

        notified_to = None
        if notify:
            try:
                recipient = None
                if vendor.account and vendor.account.email:
                    recipient = vendor.account.email.strip().lower()
                if not recipient:
                    contact = ContactInfo.query.filter_by(parent_id=vendor_id, parent_type="vendor").first()
                    recipient = (contact.email or "").strip().lower() if contact and contact.email else None

                if recipient:
                    msg = Message(
                        subject="Hash Vendor Dashboard Credentials Updated",
                        recipients=[recipient],
                    )
                    msg.body = (
                        f"Hello {vendor.owner_name or 'Partner'},\n\n"
                        f"Your dashboard credentials were reset by super admin.\n"
                        f"Cafe: {vendor.cafe_name}\n"
                        f"Login email: {recipient}\n"
                        f"Temporary password: {password}\n\n"
                        "Please login and change your password immediately.\n"
                        "Team Hash"
                    )
                    mail.send(msg)
                    notified_to = recipient
            except Exception as exc:
                current_app.logger.warning("Password reset email failed for vendor %s: %s", vendor_id, exc)

        return True, "Password reset", {
            "vendor_id": vendor_id,
            "account_scope_vendor_ids": vendor_ids_scope,
            "temporary_password": password,
            "notified_to": notified_to,
        }

    @staticmethod
    def list_subscription_models():
        url = f"{SuperAdminService._dashboard_service_url()}/api/packages/admin/catalog"
        response = requests.get(url, headers=SuperAdminService._admin_proxy_headers(), timeout=10)
        if response.status_code >= 400:
            try:
                payload = response.json()
            except Exception:
                payload = {"error": response.text}
            return False, payload
        body = response.json()
        return True, body.get("models", [])

    @staticmethod
    def update_subscription_models(models: List[Dict[str, Any]]):
        payload = {"models": models}
        url = f"{SuperAdminService._dashboard_service_url()}/api/packages/admin/catalog"
        response = requests.put(url, json=payload, headers=SuperAdminService._admin_proxy_headers(), timeout=12)
        if response.status_code >= 400:
            try:
                out = response.json()
            except Exception:
                out = {"error": response.text}
            return False, out
        body = response.json()
        return True, body.get("models", [])

    @staticmethod
    def send_deactivation_notice(vendor_id: int, reason: Optional[str] = None, sent_by: str = "super_admin"):
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return False, "Vendor not found", None

        recipient = None
        if vendor.account and vendor.account.email:
            recipient = (vendor.account.email or "").strip().lower()
        if not recipient:
            contact = ContactInfo.query.filter_by(parent_id=vendor_id, parent_type="vendor").first()
            recipient = (contact.email or "").strip().lower() if contact and contact.email else None
        if not recipient:
            return False, "No vendor email available for notification", None

        losses = [
            "Your cafe will be hidden from Hash consumer app listing.",
            "New app-origin bookings will stop while inactive.",
            "Active subscription benefits and campaign traffic will pause.",
            "Realtime discoverability and wallet users cannot find your cafe."
        ]
        reason_text = (reason or "").strip()
        reason_block = f"Reason: {reason_text}\n\n" if reason_text else ""
        msg = Message(
            subject=f"Hash For Gamers · Cafe Status Update ({vendor.cafe_name})",
            recipients=[recipient],
        )
        msg.body = (
            f"Hello {vendor.owner_name or 'Partner'},\n\n"
            f"We are notifying you that cafe '{vendor.cafe_name}' may be marked inactive on Hash For Gamers.\n\n"
            f"{reason_block}"
            "What you lose while inactive:\n"
            f"- {losses[0]}\n- {losses[1]}\n- {losses[2]}\n- {losses[3]}\n\n"
            "To avoid deactivation, please renew subscription and complete pending compliance items.\n\n"
            "Regards,\nHash For Gamers Ops"
        )
        mail.send(msg)

        SuperAdminService._ensure_deactivation_notice_table()
        if SuperAdminService._has_table("vendor_deactivation_notifications"):
            db.session.execute(
                text(
                    """
                    INSERT INTO vendor_deactivation_notifications
                    (vendor_id, sent_to_email, reason, loss_summary, sent_by, sent_at)
                    VALUES (:vendor_id, :sent_to_email, :reason, :loss_summary, :sent_by, now())
                    """
                ),
                {
                    "vendor_id": int(vendor_id),
                    "sent_to_email": recipient,
                    "reason": reason_text or None,
                    "loss_summary": " | ".join(losses),
                    "sent_by": sent_by,
                },
            )
            db.session.commit()

        summary = SuperAdminService._deactivation_notice_summary_map([int(vendor_id)]).get(int(vendor_id), {"sent_count": 1, "last_sent_at": datetime.utcnow()})
        return True, "Deactivation notice sent", {"vendor_id": int(vendor_id), "sent_to": recipient, **summary}

    @staticmethod
    def get_deactivation_notice_summary(vendor_id: int) -> Dict[str, Any]:
        summary = SuperAdminService._deactivation_notice_summary_map([int(vendor_id)]).get(int(vendor_id))
        return summary or {"sent_count": 0, "last_sent_at": None}

    @staticmethod
    def change_subscription(vendor_id: int, package_code: str, immediate: bool = True, unit_amount: float = 0.0):
        payload = {
            "package_code": package_code,
            "immediate": bool(immediate),
            "unit_amount": float(unit_amount or 0),
        }
        url = f"{SuperAdminService._dashboard_service_url()}/api/vendors/{vendor_id}/subscription/change"
        response = requests.post(url, json=payload, headers=SuperAdminService._admin_proxy_headers(), timeout=8)
        if response.status_code >= 400:
            try:
                msg = response.json()
            except Exception:
                msg = {"error": response.text}
            return False, msg
        SuperAdminService.update_vendor_status(vendor_id, "active", changed_by="subscription_change")
        return True, response.json()

    @staticmethod
    def provision_default_subscription(vendor_id: int):
        url = f"{SuperAdminService._dashboard_service_url()}/api/vendors/{vendor_id}/subscription/provision-default"
        response = requests.post(url, json={}, headers=SuperAdminService._admin_proxy_headers(), timeout=8)
        if response.status_code >= 400:
            try:
                msg = response.json()
            except Exception:
                msg = {"error": response.text}
            return False, msg
        SuperAdminService.update_vendor_status(vendor_id, "active", changed_by="subscription_default")
        return True, response.json()
