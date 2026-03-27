# app/controllers.py

from flask import Blueprint, request, jsonify, current_app
import os
import re
import random
import string
from services.services import VendorService
from werkzeug.utils import secure_filename
import json
from flask_mail import Message
from services.cloudinary_services import CloudinaryGameImageService
from models.document import Document

from services.utils import process_files

from models.vendor import Vendor
from models.vendorAccount import VendorAccount
from models.contactInfo import ContactInfo
from models.uploadedImage import Image

from models.bookingQueue import BookingQueue
from models.booking import Booking
from models.accessBookingCode import AccessBookingCode
from db.extensions import db, mail, redis_client
from services.otp_service import OTPService
from services.email_template import build_hfg_email_html
from models.transaction import Transaction
from models.availableGame import AvailableGame
from models.slots import Slot
from models.vendorDaySlotConfig import VendorDaySlotConfig


from sqlalchemy import text, tuple_, func, bindparam
from models.timing import Timing

import requests

from pytz import timezone
from datetime import datetime as dt, timedelta, date, time as dtime
from datetime import timezone as dt_timezone  # ✅ add this import near the top
datetime = dt

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    import pytz
    IST = pytz.timezone("Asia/Kolkata")

INTERNAL_WS_URL = "https://hfg-dashboard-h9qq.onrender.com/internal/ws/unlock"
DASHBOARD_SERVICE_URL = os.getenv("DASHBOARD_SERVICE_URL", "https://hfg-dashboard.onrender.com")
BOOKING_SERVICE_URL = os.getenv("BOOKING_SERVICE_URL", "https://hfg-booking.onrender.com")

vendor_bp = Blueprint('vendor', __name__)

GRACE_MIN = 30
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx'}
ALLOWED_VENDOR_DOCUMENT_TYPES = {
    "business_registration",
    "owner_identification_proof",
    "tax_identification_number",
    "bank_acc_details",
}
WEEKDAY_MAP = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6
}
FULL_DAY_TO_SHORT = {
    "monday": "mon",
    "tuesday": "tue",
    "wednesday": "wed",
    "thursday": "thu",
    "friday": "fri",
    "saturday": "sat",
    "sunday": "sun",
}

# Adjust this window as needed (e.g., 365 for a year)
FUTURE_WINDOW_DAYS = int(os.getenv("SLOT_ROLLING_WINDOW_DAYS", "60"))
SELF_ONBOARD_OTP_EXPIRY_SECONDS = int(os.getenv("SELF_ONBOARD_OTP_EXPIRY_SECONDS", "300"))
SELF_ONBOARD_VERIFY_EXPIRY_SECONDS = int(os.getenv("SELF_ONBOARD_VERIFY_EXPIRY_SECONDS", "1800"))
SELF_ONBOARD_OTP_COOLDOWN_SECONDS = int(os.getenv("SELF_ONBOARD_OTP_COOLDOWN_SECONDS", "45"))
SELF_ONBOARD_DASHBOARD_URL = (os.getenv("SELF_ONBOARD_DASHBOARD_URL") or "https://dashboard.hashforgamers.com").rstrip("/")


def _normalize_email(value):
    return str(value or "").strip().lower()


def _is_valid_email(value):
    return re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value or "") is not None


def _normalize_phone(value):
    return re.sub(r"\D", "", str(value or ""))[-10:]


def _normalize_whitespace(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_cafe_name(value):
    return _normalize_whitespace(value).lower()


def _self_onboard_duplicate_reason(email, owner_phone=None):
    normalized_email = _normalize_email(email)
    normalized_phone = _normalize_phone(owner_phone)

    if normalized_email:
        vendor_account = (
            VendorAccount.query
            .filter(func.lower(VendorAccount.email) == normalized_email)
            .first()
        )
        if vendor_account:
            linked_vendor = Vendor.query.filter(Vendor.account_id == vendor_account.id).first()
            if linked_vendor:
                return (
                    "This owner email is already onboarded with Hash. "
                    "Use your dashboard account and add new branches from Select Cafe.",
                    "existing_owner_email",
                )

    if normalized_phone and re.match(r"^[6-9][0-9]{9}$", normalized_phone):
        existing_contact = (
            ContactInfo.query
            .filter(
                ContactInfo.parent_type == "vendor",
                ContactInfo.phone == normalized_phone,
            )
            .first()
        )
        if existing_contact:
            linked_vendor = Vendor.query.get(existing_contact.parent_id)
            if linked_vendor:
                return (
                    "This owner phone is already linked to an onboarded cafe. "
                    "Use the existing owner account and add branches from Select Cafe.",
                    "existing_owner_phone",
                )

    return None


def _validate_self_onboard_payload(data):
    owner_name = _normalize_whitespace(data.get("owner_name"))
    cafe_name = _normalize_whitespace(data.get("cafe_name"))
    contact_info = data.get("contact_info") or {}
    address = data.get("physicalAddress") or {}
    timing = data.get("timing") or {}
    games = data.get("available_games") or []
    business_registration = data.get("business_registration_details") or {}
    owner_proof = data.get("owner_proof_details") or {}

    owner_email = _normalize_email(contact_info.get("email"))
    owner_phone = _normalize_phone(contact_info.get("phone"))
    city = _normalize_whitespace(address.get("city"))
    state = _normalize_whitespace(address.get("state"))
    pincode = str(address.get("zipCode") or "").strip()

    if len(owner_name) < 2 or len(owner_name) > 80:
        return "Owner name must be between 2 and 80 characters."
    if re.match(r"^[A-Za-z][A-Za-z\s.'-]+$", owner_name) is None:
        return "Owner name format is invalid."
    if len(cafe_name) < 3 or len(cafe_name) > 120:
        return "Cafe name must be between 3 and 120 characters."
    if not _is_valid_email(owner_email):
        return "Valid owner email is required."
    if re.match(r"^[6-9][0-9]{9}$", owner_phone) is None:
        return "Owner phone must be a valid 10-digit mobile number."
    if len(_normalize_whitespace(address.get("street"))) < 5:
        return "Address should be at least 5 characters."
    if len(city) < 2 or len(state) < 2:
        return "City and state are required."
    if re.match(r"^[0-9]{6}$", pincode) is None:
        return "Pincode must be 6 digits."
    if len(_normalize_whitespace(business_registration.get("registration_type"))) < 3:
        return "Business registration document type is required."
    if len(_normalize_whitespace(business_registration.get("registration_number"))) < 3:
        return "Business registration number is required."
    if len(_normalize_whitespace(owner_proof.get("type"))) < 3:
        return "Owner proof type is required."
    if len(_normalize_whitespace(owner_proof.get("number"))) < 4:
        return "Owner proof number is required."

    lat_raw = address.get("latitude")
    lng_raw = address.get("longitude")
    try:
        lat = float(lat_raw)
        lng = float(lng_raw)
    except (TypeError, ValueError):
        return "Latitude and longitude are required."
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return "Latitude/longitude is invalid."

    if not isinstance(games, list) or len(games) == 0:
        return "At least one console inventory item is required."
    enabled_games = 0
    for game in games:
        total_slot = int(game.get("total_slot") or 0)
        rate = float(game.get("rate_per_slot") or 0)
        if total_slot < 0 or total_slot > 500:
            return "Console quantity must be between 0 and 500."
        if rate < 0 or rate > 100000:
            return "Rate per slot is out of allowed range."
        if total_slot > 0:
            enabled_games += 1
    if enabled_games == 0:
        return "At least one console type must have quantity greater than zero."

    if not isinstance(timing, dict) or not timing:
        return "Operating hours are required."

    has_open_day = False
    for day_key, day_data in timing.items():
        if not isinstance(day_data, dict):
            return f"Invalid timing payload for {day_key}."
        if day_data.get("closed"):
            continue
        has_open_day = True
        slot_duration = int(day_data.get("slot_duration") or 0)
        if slot_duration not in (15, 30, 45, 60, 90, 120):
            return "Slot duration must be one of 15, 30, 45, 60, 90, or 120 minutes."
        open_time = str(day_data.get("open") or "").strip()
        close_time = str(day_data.get("close") or "").strip()
        is_24_hours = bool(day_data.get("is_24_hours"))
        if is_24_hours:
            continue
        open_parsed = safe_strptime(open_time, "%I:%M %p")
        close_parsed = safe_strptime(close_time, "%I:%M %p")
        if not open_parsed or not close_parsed:
            return f"Invalid opening/closing time for {day_key}."
        if open_time == close_time:
            return f"Open and close time cannot be the same for {day_key}."

    if not has_open_day:
        return "At least one day must be open."

    return None


def _self_onboard_otp_key(email):
    return f"self_onboard:otp:{email}"


def _self_onboard_otp_cooldown_key(email):
    return f"self_onboard:otp_cooldown:{email}"


def _self_onboard_verify_key(email):
    return f"self_onboard:verified:{email}"


def _self_onboard_verify_token_key(token):
    return f"self_onboard:verify_token:{token}"


def _consume_self_onboard_verification_token(token, email):
    token_key = _self_onboard_verify_token_key(token)
    stored_email = _normalize_email(redis_client.get(token_key))
    normalized_email = _normalize_email(email)
    if not stored_email:
        return False, "Email verification token expired. Please verify email again."
    if stored_email != normalized_email:
        return False, "Email verification token does not match the owner email."
    redis_client.delete(token_key)
    redis_client.setex(_self_onboard_verify_key(normalized_email), SELF_ONBOARD_VERIFY_EXPIRY_SECONDS, "1")
    return True, None


def normalize_day_key(day_value):
    raw = str(day_value or "").strip().lower()
    if raw in WEEKDAY_MAP:
        return raw
    if raw in FULL_DAY_TO_SHORT:
        return FULL_DAY_TO_SHORT[raw]
    if len(raw) >= 3:
        short = raw[:3]
        if short in WEEKDAY_MAP:
            return short
    return None


def parse_time_flexible(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            return dt.strptime(raw, fmt).time()
        except ValueError:
            continue
    return None


def _generate_blocks(anchor_day, start_time, end_time, slot_duration):
    start_dt = dt.combine(anchor_day, start_time)
    end_dt = dt.combine(anchor_day, end_time)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)

    blocks = []
    cur_dt = start_dt
    while cur_dt < end_dt:
        nxt_dt = cur_dt + timedelta(minutes=int(slot_duration))
        if nxt_dt > end_dt:
            break
        block_start_t = cur_dt.time()
        block_end_t = (
            nxt_dt.time() if nxt_dt.date() == cur_dt.date()
            else (nxt_dt - timedelta(days=1)).time()
        )
        blocks.append((block_start_t, block_end_t))
        cur_dt = nxt_dt
    return blocks


def _apply_slot_rows_for_day(vendor_id, games, target_dates, blocks, is_enabled):
    updated_days = 0
    inserted_rows = 0

    if not target_dates:
        return {"updated_days": 0, "inserted_rows": 0}

    delete_dates_sql = text(f"""
        DELETE FROM VENDOR_{vendor_id}_SLOT
        WHERE vendor_id = :vendor_id
          AND date IN :target_dates
    """).bindparams(bindparam("target_dates", expanding=True))

    # Clear day rows first if this day is disabled.
    if not is_enabled:
        db.session.execute(
            delete_dates_sql,
            {"vendor_id": vendor_id, "target_dates": target_dates},
        )
        return {"updated_days": len(target_dates), "inserted_rows": 0}

    if not blocks:
        db.session.execute(
            delete_dates_sql,
            {"vendor_id": vendor_id, "target_dates": target_dates},
        )
        return {"updated_days": len(target_dates), "inserted_rows": 0}

    game_totals = {int(g.id): int(g.total_slot or 0) for g in games if int(g.total_slot or 0) > 0}
    if not game_totals:
        return {"updated_days": 0, "inserted_rows": 0}

    game_ids = list(game_totals.keys())
    existing_slots = (
        Slot.query
        .filter(
            Slot.gaming_type_id.in_(game_ids),
            tuple_(Slot.start_time, Slot.end_time).in_(blocks),
        )
        .all()
    )
    slot_id_map = {(int(s.gaming_type_id), s.start_time, s.end_time): int(s.id) for s in existing_slots}

    to_create = []
    for game_id in game_ids:
        for st, et in blocks:
            key = (game_id, st, et)
            if key in slot_id_map:
                continue
            to_create.append(
                Slot(
                    gaming_type_id=game_id,
                    start_time=st,
                    end_time=et,
                    available_slot=game_totals[game_id],
                    is_available=False,
                )
            )

    if to_create:
        db.session.add_all(to_create)
        db.session.flush()
        for s in to_create:
            slot_id_map[(int(s.gaming_type_id), s.start_time, s.end_time)] = int(s.id)

    insert_sql = text(f"""
        INSERT INTO VENDOR_{vendor_id}_SLOT (vendor_id, slot_id, date, available_slot, is_available)
        VALUES (:vendor_id, :slot_id, :date, :available_slot, :is_available)
    """)

    db.session.execute(
        delete_dates_sql,
        {"vendor_id": vendor_id, "target_dates": target_dates},
    )

    batch = []
    for d in target_dates:
        for game_id, total in game_totals.items():
            for st, et in blocks:
                slot_id = slot_id_map.get((game_id, st, et))
                if not slot_id:
                    continue
                batch.append(
                    {
                        "vendor_id": vendor_id,
                        "slot_id": slot_id,
                        "date": d,
                        "available_slot": total,
                        "is_available": True,
                    }
                )

    if batch:
        db.session.execute(insert_sql, batch)
        inserted_rows = len(batch)

    return {"updated_days": len(target_dates), "inserted_rows": inserted_rows}


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_json(data, required_fields):
    """Validate the JSON data for required fields."""
    missing_fields = [field for field in required_fields if field not in data]
    return missing_fields


def upload_documents_to_cloudinary(files, vendor_id, cafe_name):
    """
    Upload vendor documents to Cloudinary and return URLs
    """
    document_urls = {}
    
    for doc_type, file in files.items():
        try:
            current_app.logger.info(f"Uploading {doc_type} to Cloudinary for vendor {vendor_id}")
            
            # Use Cloudinary service for document upload
            upload_result = CloudinaryGameImageService.upload_vendor_document(
                file, 
                cafe_name,
                doc_type, 
                vendor_id
            )
            
            if upload_result['success']:
                document_urls[doc_type] = {
                    'url': upload_result['url'],
                    'public_id': upload_result['public_id']
                }
                current_app.logger.info(f"Successfully uploaded {doc_type}: {upload_result['url']}")
            else:
                current_app.logger.error(f"Failed to upload {doc_type}: {upload_result['error']}")
                raise Exception(f"Failed to upload {doc_type} to Cloudinary")
        except Exception as e:
            current_app.logger.error(f"Error uploading {doc_type}: {str(e)}")
            raise Exception(f"Document upload failed for {doc_type}")
    
    return document_urls

def save_vendor_documents(vendor_id, document_urls, document_submitted):
    """Save uploaded document metadata once; avoid duplicate inserts and loop commits."""
    try:
        saved_count = 0
        for doc_type, doc_info in document_urls.items():
            if not document_submitted.get(doc_type, False):
                continue

            existing = Document.query.filter_by(vendor_id=vendor_id, document_type=doc_type).first()
            if existing:
                existing.document_url = doc_info['url']
                existing.public_id = doc_info['public_id']
                existing.status = 'unverified'
                existing.uploaded_at = dt.utcnow()
            else:
                db.session.add(
                    Document(
                        vendor_id=vendor_id,
                        document_type=doc_type,
                        document_url=doc_info['url'],
                        public_id=doc_info['public_id'],
                        uploaded_at=dt.utcnow(),
                        status='unverified'
                    )
                )
            saved_count += 1

        db.session.commit()
        current_app.logger.info(f"Saved {saved_count} documents for vendor {vendor_id}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving documents to database: {str(e)}")
        raise e

@vendor_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


# def process_files(request, document_types):
#     """Process uploaded files and ensure they meet requirements."""
#     files = {}
#     for doc_type in document_types:
#         if doc_type in request.files:
#             file = request.files[doc_type]
#             if file and allowed_file(file.filename):
#                 filename = secure_filename(file.filename)
#                 files[doc_type] = file
#             else:
#                 return None, f'Invalid file for {doc_type}. Only PDF allowed.'
#         else:
#             # Check if the document is marked as submitted but no file is provided
#             if data.get('document_submitted', {}).get(doc_type, False):
#                 return None, f'Missing file for {doc_type}'
#     return files, None




def safe_strptime(date_str, format_str):
    """Safely parse date string, handling None and invalid values"""
    if date_str is None or date_str == '':
        return None
    
    if not isinstance(date_str, str):
        current_app.logger.warning(f"Date string is not str type: {type(date_str)}")
        return None
    
    try:
        return dt.strptime(date_str, format_str)
        return dt.strptime(date_str, format_str)
    except ValueError as e:
        current_app.logger.error(f"Error parsing date '{date_str}' with format '{format_str}': {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error parsing date '{date_str}': {e}")
        return None


@vendor_bp.route('/self-onboard/send-email-otp', methods=['POST'])
def send_self_onboard_email_otp():
    try:
        data = request.get_json(silent=True) or {}
        email = _normalize_email(data.get("email"))
        cafe_name = str(data.get("cafe_name") or "your gaming cafe").strip()
        owner_phone = _normalize_phone(data.get("owner_phone"))

        if not _is_valid_email(email):
            return jsonify({"success": False, "message": "Valid email is required"}), 400
        if owner_phone and re.match(r"^[6-9][0-9]{9}$", owner_phone) is None:
            return jsonify({"success": False, "message": "Owner phone must be a valid 10-digit mobile number"}), 400

        duplicate_info = _self_onboard_duplicate_reason(email, owner_phone=owner_phone)
        if duplicate_info:
            duplicate_reason, duplicate_code = duplicate_info
            return jsonify({
                "success": False,
                "message": duplicate_reason,
                "code": duplicate_code,
                "dashboard_url": SELF_ONBOARD_DASHBOARD_URL
            }), 409

        cooldown_key = _self_onboard_otp_cooldown_key(email)
        if redis_client.exists(cooldown_key):
            return jsonify({
                "success": False,
                "message": "Please wait before requesting another OTP."
            }), 429

        otp = ''.join(random.choices(string.digits, k=6))
        redis_client.setex(_self_onboard_otp_key(email), SELF_ONBOARD_OTP_EXPIRY_SECONDS, otp)
        redis_client.setex(cooldown_key, SELF_ONBOARD_OTP_COOLDOWN_SECONDS, "1")
        redis_client.delete(_self_onboard_verify_key(email))

        msg = Message(
            subject="Hash Self Onboarding - Email Verification OTP",
            recipients=[email],
            sender=current_app.config.get("MAIL_DEFAULT_SENDER"),
        )
        msg.body = (
            f"Hello,\n\n"
            f"Use OTP {otp} to verify your email for Hash cafe onboarding.\n"
            f"Cafe: {cafe_name}\n\n"
            f"This OTP expires in {SELF_ONBOARD_OTP_EXPIRY_SECONDS // 60} minutes.\n"
            f"If you did not request this, you can ignore this email.\n\n"
            "Team Hash"
        )
        otp_html = f"""
        <div style="font-family:Arial,Helvetica,sans-serif;line-height:1.7;color:#e5e7eb;max-width:560px;margin:0 auto;">
          <h2 style="margin:0 0 10px 0;color:#f8fafc;font-size:28px;line-height:1.25;">Hash Cafe Self Onboarding</h2>
          <p style="margin:0 0 12px 0;color:#cbd5e1;">Use this OTP to verify your email:</p>

          <div style="margin:0 0 14px 0;">
            <span style="display:inline-block;background:#f8fafc;border:1px solid #dbeafe;border-radius:10px;padding:12px 18px;color:#0f172a;font-size:34px;font-weight:700;letter-spacing:8px;">
              {otp}
            </span>
          </div>

          <div style="background:#08142c;border:1px solid #1e3a8a;border-radius:10px;padding:12px 14px;margin:0 0 12px 0;">
            <p style="margin:0 0 6px 0;color:#93c5fd;font-size:13px;text-transform:uppercase;letter-spacing:.06em;">Cafe</p>
            <p style="margin:0;color:#f8fafc;font-size:16px;font-weight:700;">{cafe_name}</p>
          </div>

          <p style="margin:0 0 8px 0;color:#cbd5e1;">This OTP expires in {SELF_ONBOARD_OTP_EXPIRY_SECONDS // 60} minutes.</p>
          <p style="margin:0;color:#94a3b8;font-size:13px;">If you did not request this, ignore this email.</p>
        </div>
        """
        msg.html = build_hfg_email_html(
            subject=msg.subject,
            content_html=otp_html,
            preview_text=f"Your Hash onboarding OTP is {otp}",
        )

        mail.send(msg)

        return jsonify({
            "success": True,
            "message": "OTP sent successfully.",
            "otp_expires_in_seconds": SELF_ONBOARD_OTP_EXPIRY_SECONDS
        }), 200
    except Exception as exc:
        current_app.logger.error(f"send_self_onboard_email_otp failed: {str(exc)}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to send OTP"}), 500


@vendor_bp.route('/self-onboard/verify-email-otp', methods=['POST'])
def verify_self_onboard_email_otp():
    try:
        data = request.get_json(silent=True) or {}
        email = _normalize_email(data.get("email"))
        otp = str(data.get("otp") or "").strip()

        if not _is_valid_email(email) or not otp:
            return jsonify({"success": False, "message": "Email and OTP are required"}), 400

        stored_otp = str(redis_client.get(_self_onboard_otp_key(email)) or "").strip()
        if not stored_otp:
            return jsonify({"success": False, "message": "OTP expired. Please request again."}), 400
        if stored_otp != otp:
            return jsonify({"success": False, "message": "Invalid OTP"}), 400

        redis_client.delete(_self_onboard_otp_key(email))
        redis_client.setex(_self_onboard_verify_key(email), SELF_ONBOARD_VERIFY_EXPIRY_SECONDS, "1")
        verification_token = ''.join(random.choices(string.ascii_letters + string.digits, k=40))
        redis_client.setex(
            _self_onboard_verify_token_key(verification_token),
            SELF_ONBOARD_VERIFY_EXPIRY_SECONDS,
            email,
        )

        return jsonify({
            "success": True,
            "message": "Email verified successfully.",
            "verification_token": verification_token,
            "verification_expires_in_seconds": SELF_ONBOARD_VERIFY_EXPIRY_SECONDS
        }), 200
    except Exception as exc:
        current_app.logger.error(f"verify_self_onboard_email_otp failed: {str(exc)}", exc_info=True)
        return jsonify({"success": False, "message": "OTP verification failed"}), 500


@vendor_bp.route('/onboard', methods=['POST'])
def onboard_vendor():
    current_app.logger.debug("Received onboarding request")

    if not request.content_type.startswith('multipart/form-data'):
        current_app.logger.warning("Invalid content type for onboarding request")
        return jsonify({'message': 'Content-Type must be multipart/form-data'}), 400

    json_data = request.form.get('json')
    if not json_data:
        current_app.logger.warning("Missing JSON data in form")
        return jsonify({'message': 'Missing JSON data in form'}), 400

    try:
        data = json.loads(json_data)
        current_app.logger.debug(f"Parsed JSON data: {data}")
    except json.JSONDecodeError:
        current_app.logger.error("Invalid JSON format in form data")
        return jsonify({'message': 'Invalid JSON format'}), 400

    onboarding_source = str(data.get("onboarding_source", "")).strip().lower()

    if onboarding_source == "self_onboard":
        validation_error = _validate_self_onboard_payload(data)
        if validation_error:
            return jsonify({'message': validation_error}), 400

    verification_token = str(data.pop("self_onboard_email_verification_token", "") or "").strip()
    contact_email = _normalize_email((data.get("contact_info") or {}).get("email"))
    if verification_token:
        valid, verify_error = _consume_self_onboard_verification_token(verification_token, contact_email)
        if not valid:
            current_app.logger.warning(f"Self-onboard email verification failed: {verify_error}")
            return jsonify({'message': verify_error}), 400
    elif onboarding_source == "self_onboard":
        return jsonify({'message': 'Email verification is required before onboarding'}), 400

    if onboarding_source == "self_onboard":
        duplicate_info = _self_onboard_duplicate_reason(
            contact_email,
            owner_phone=(data.get("contact_info") or {}).get("phone"),
        )
        if duplicate_info:
            duplicate_reason, duplicate_code = duplicate_info
            return jsonify({
                'success': False,
                'message': duplicate_reason,
                'code': duplicate_code,
                'dashboard_url': SELF_ONBOARD_DASHBOARD_URL
            }), 409

    # Extract vendor_account_email from contact_info

    # Transform timing data from day-wise to single opening/closing times
    if 'timing' in data:
        current_app.logger.debug(f"Raw timing data: {data['timing']}")
        
        # Find the first open day to get opening and closing times
        opening_time = None
        closing_time = None
        opening_days = {}
        
        for day, day_data in data['timing'].items():
            if day_data.get('closed', False):
                opening_days[day] = False
            else:
                opening_days[day] = True
                open_time_str = day_data.get('open')
                close_time_str = day_data.get('close')
                
                # Validate time strings
                if open_time_str and close_time_str:
                    open_parsed = safe_strptime(open_time_str, "%I:%M %p")
                    close_parsed = safe_strptime(close_time_str, "%I:%M %p")
                    
                    if open_parsed and close_parsed:
                        # Use the first valid timing as the general opening/closing time
                        if not opening_time:
                            opening_time = open_time_str
                            closing_time = close_time_str
                    else:
                        current_app.logger.warning(f"Invalid time format for {day}: open={open_time_str}, close={close_time_str}")
                        return jsonify({'message': f'Invalid time format for {day}'}), 400
                else:
                    current_app.logger.warning(f"Missing time data for {day}")
                    return jsonify({'message': f'Missing time data for {day}'}), 400
        
        # Check if at least one day is open
        if not any(opening_days.values()):
            current_app.logger.warning("No open days found")
            return jsonify({'message': 'At least one day must be open'}), 400
            
        if not opening_time or not closing_time:
            current_app.logger.warning("No valid opening/closing times found")
            return jsonify({'message': 'Valid opening and closing times are required'}), 400
        
        # Transform timing data to match VendorService expectations
        data['timing'] = {
            'opening_time': opening_time,
            'closing_time': closing_time
        }
        
        # Add opening_day data in the expected format
        data['opening_day'] = opening_days
        current_app.logger.debug(f"Transformed timing data: {data['timing']}")
        current_app.logger.debug(f"Opening days data: {data['opening_day']}")

    # Transform available_games data from list to dict
    if 'available_games' in data and isinstance(data['available_games'], list):
        games_dict = {}
        for game in data['available_games']:
            if game.get('name'):
                games_dict[game['name']] = {
                    'total_slot': game.get('total_slot', 0),
                    'single_slot_price': game.get('rate_per_slot', 0)
                }
        data['available_games'] = games_dict
        current_app.logger.debug(f"Transformed games data: {data['available_games']}")

    # Transform physicalAddress data
    if 'physicalAddress' in data:
        address_data = data['physicalAddress']
        transformed_address = {
            'address_type': 'business',
            'addressLine1': address_data.get('street', ''),
            'addressLine2': address_data.get('city', ''),
            'pincode': address_data.get('zipCode', ''),
            'state': address_data.get('state', ''),
            'country': address_data.get('country', ''),
            'latitude': address_data.get('latitude'),
            'longitude': address_data.get('longitude')
        }
        data['physicalAddress'] = transformed_address
        current_app.logger.debug(f"Transformed address data: {data['physicalAddress']}")

    # Transform business_registration_details
    if 'business_registration_details' in data:
        reg_data = data['business_registration_details']
        if 'registration_date' not in reg_data:
            reg_data['registration_date'] = data.get('opening_day', dt.now().strftime('%Y-%m-%d'))
        current_app.logger.debug(f"Business registration data: {reg_data}")

    # Validate required fields
    current_app.logger.debug("Validating required fields")
    required_fields = [
        'cafe_name', 'owner_name', 'contact_info', 'physicalAddress',
        'business_registration_details', 'document_submitted',
        'timing', 'opening_day', 'available_games'
    ]
    missing_fields = validate_json(data, required_fields)
    if missing_fields:
        current_app.logger.warning(f"Missing fields: {missing_fields}")
        return jsonify({'message': f'Missing fields: {", ".join(missing_fields)}'}), 400

    # Process files for Cloudinary upload
    current_app.logger.debug("Started Processing Files for Cloudinary")
    document_types = [
        'business_registration', 'owner_identification_proof',
        'tax_identification_number', 'bank_acc_details'
    ]

    files, error_message = process_files(request, data, document_types)
    if error_message:
        current_app.logger.error(f"File processing error: {error_message}")
        return jsonify({'message': error_message}), 400
    
    try:
        # Onboard the vendor
        current_app.logger.debug("Onboarding vendor...")
        current_app.logger.debug(f"Final data being sent to VendorService: {data}")
        vendor = VendorService.onboard_vendor(data, files)

        # Upload documents to Cloudinary
        current_app.logger.debug("Uploading documents to Cloudinary...")
        document_urls = upload_documents_to_cloudinary(files, vendor.id, vendor.cafe_name)
        
        # Save document information to database
        save_vendor_documents(vendor.id, document_urls, data['document_submitted'])

        # Generate credentials and notify
        current_app.logger.debug("Generating credentials and notifications...")
        VendorService.generate_credentials_and_notify(vendor)
        
        current_app.logger.info(f"Vendor onboarded successfully: {vendor.id}")
        return jsonify({
            'message': 'Vendor onboarded successfully', 
            'vendor_id': vendor.id,
            'documents_uploaded': len(document_urls)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Onboarding error: {e}")
        import traceback
        current_app.logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'message': 'An error occurred during onboarding', 'error': str(e)}), 500


@vendor_bp.route('/deboard/<int:vendor_id>', methods=['DELETE'])
def deboard_vendor(vendor_id):
    current_app.logger.debug(f"Received deboarding request for vendor ID: {vendor_id}")
    try:
        VendorService.deboard_vendor(vendor_id)
        current_app.logger.info(f"Vendor {vendor_id} deboarded successfully.")
        return jsonify({'message': f'Vendor {vendor_id} deboarded successfully'}), 200
    except Exception as e:
        current_app.logger.error(f"Deboarding error for vendor {vendor_id}: {e}")
        return jsonify({'message': 'An error occurred during deboarding', 'error': str(e)}), 500


@vendor_bp.route('/vendor/<int:vendor_id>/documents', methods=['GET'])
def get_unverified_documents(vendor_id):
    """API endpoint to get all unverified document file paths for a given vendor."""
    # Call the VendorService to get unverified documents
    response, status_code = VendorService.get_unverified_documents(vendor_id)
    return jsonify(response), status_code


@vendor_bp.route('/vendor/<int:vendor_id>/documents', methods=['POST'])
def upload_vendor_missing_document(vendor_id):
    """
    Upload a missing (or replace existing) required onboarding document by document_type.
    """
    try:
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({"success": False, "message": "Vendor not found"}), 404

        document_type = str(request.form.get("document_type") or "").strip().lower()
        if document_type not in ALLOWED_VENDOR_DOCUMENT_TYPES:
            return jsonify({
                "success": False,
                "message": "document_type must be one of business_registration, owner_identification_proof, tax_identification_number, bank_acc_details",
            }), 400

        file_obj = request.files.get("document")
        if not file_obj or not file_obj.filename:
            return jsonify({"success": False, "message": "document file is required"}), 400

        upload_result = CloudinaryGameImageService.upload_vendor_document(
            document_file=file_obj,
            cafe_name=vendor.cafe_name or "vendor",
            document_type=document_type,
            vendor_id=vendor_id
        )
        if not upload_result.get("success"):
            return jsonify({
                "success": False,
                "message": upload_result.get("error") or "Failed to upload document"
            }), 500

        existing = Document.query.filter_by(vendor_id=vendor_id, document_type=document_type).first()
        if existing:
            old_public_id = existing.public_id
            existing.document_url = upload_result.get("url")
            existing.public_id = upload_result.get("public_id")
            existing.status = "unverified"
            existing.uploaded_at = dt.utcnow()
            document = existing
            if old_public_id and old_public_id != existing.public_id:
                try:
                    CloudinaryGameImageService.delete_image(old_public_id)
                except Exception:
                    pass
        else:
            document = Document(
                vendor_id=vendor_id,
                document_type=document_type,
                document_url=upload_result.get("url"),
                public_id=upload_result.get("public_id"),
                uploaded_at=dt.utcnow(),
                status="unverified",
            )
            db.session.add(document)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Document uploaded and sent for verification",
            "document": {
                "id": document.id,
                "name": (document.document_type or "").replace("_", " ").title(),
                "document_type": document.document_type,
                "status": document.status,
                "uploadedAt": document.uploaded_at.isoformat() if document.uploaded_at else None,
                "documentUrl": document.document_url,
                "publicId": document.public_id,
            }
        }), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(
            "upload_vendor_missing_document failed vendor_id=%s err=%s",
            vendor_id,
            exc,
            exc_info=True,
        )
        return jsonify({"success": False, "message": "Failed to upload document"}), 500


@vendor_bp.route('/vendor/<int:vendor_id>/documents/<int:document_id>', methods=['PUT'])
def replace_vendor_document(vendor_id, document_id):
    """
    Replace an existing vendor document file.
    Note: Replaced doc status becomes 'unverified' and must be re-verified by super admin.
    """
    try:
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({"success": False, "message": "Vendor not found"}), 404

        document = Document.query.filter_by(id=document_id, vendor_id=vendor_id).first()
        if not document:
            return jsonify({"success": False, "message": "Document not found"}), 404

        file_obj = request.files.get("document")
        if not file_obj or not file_obj.filename:
            return jsonify({"success": False, "message": "document file is required"}), 400

        upload_result = CloudinaryGameImageService.upload_vendor_document(
            document_file=file_obj,
            cafe_name=vendor.cafe_name or "vendor",
            document_type=document.document_type or "document",
            vendor_id=vendor_id
        )
        if not upload_result.get("success"):
            return jsonify({
                "success": False,
                "message": upload_result.get("error") or "Failed to upload document"
            }), 500

        old_public_id = document.public_id
        document.document_url = upload_result.get("url")
        document.public_id = upload_result.get("public_id")
        document.status = "unverified"
        document.uploaded_at = dt.utcnow()
        db.session.commit()

        # Best-effort cleanup for old file (ignore failures).
        if old_public_id and old_public_id != document.public_id:
            try:
                CloudinaryGameImageService.delete_image(old_public_id)
            except Exception:
                pass

        return jsonify({
            "success": True,
            "message": "Document updated and sent for re-verification",
            "document": {
                "id": document.id,
                "name": (document.document_type or "").replace("_", " ").title(),
                "status": document.status,
                "uploadedAt": document.uploaded_at.isoformat() if document.uploaded_at else None,
                "documentUrl": document.document_url,
                "publicId": document.public_id,
            }
        }), 200
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error("Failed to replace document vendor_id=%s document_id=%s err=%s", vendor_id, document_id, exc)
        return jsonify({"success": False, "message": "Failed to update document"}), 500

@vendor_bp.route('/vendor/document/<int:document_id>/verify', methods=['POST'])
def verify_document(document_id):
    """API endpoint to mark a document as verified and update vendor status if applicable."""
    response, status_code = VendorService.verify_document(document_id)
    return jsonify(response), status_code

@vendor_bp.route('/vendor/documents/verify', methods=['POST'])
def verify_documents():
    """
    API to verify specified documents and update vendor status if all documents are verified.
    """
    data = request.get_json()
    if not data or 'document_ids' not in data:
        return jsonify({'message': 'Missing required field: document_ids'}), 400
    
    document_ids = data['document_ids']
    
    # Call the VendorService to update documents' status and check vendor status
    response, status_code = VendorService.verify_documents_and_update_vendor(document_ids)
    return jsonify(response), status_code

@vendor_bp.route('/vendor/dashboard', methods=['GET'])
def get_vendor_dashboard():
    """
    API to retrieve all vendors with their statuses and relevant information for the salesperson dashboard.
    """
    try:
        response_data = VendorService.get_all_vendors_with_status()
        return jsonify(response_data), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching vendor dashboard: {e}")
        return jsonify({'message': 'An error occurred while fetching vendor data', 'error': str(e)}), 500

@vendor_bp.route('/vendor/getAllGamingCafe', methods=['GET'])
def get_all_gaming_cafe():
    """
    API to retrieve all vendors with their statuses and relevant information
    for app/dashboard listing.
    By default returns only active cafes; pass include_inactive=true for admin/debug.
    """
    try:
        include_inactive = str(request.args.get("include_inactive", "")).strip().lower() in {"1", "true", "yes", "y"}
        response_data = VendorService.get_all_gaming_cafe(include_inactive=include_inactive)
        return jsonify(response_data), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching vendor dashboard: {e}")
        return jsonify({'message': 'An error occurred while fetching vendor data', 'error': str(e)}), 500




@vendor_bp.route('/upload-photos/<int:vendor_id>', methods=['POST'])
def upload_photos(vendor_id):
    """API endpoint to upload photos to Google Drive."""
    try:
        # Validate vendor
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({"error": "Vendor not found"}), 404

        # Get the file from the request
        if 'photo' not in request.files:
            return jsonify({"error": "No photo provided"}), 400

        photos = request.files.getlist('photo')  # Updated to get list of photos
        if not photos:
            return jsonify({"error": "No photos selected"}), 400

        # Initialize Google Drive service
        service = VendorService.get_drive_service()

        # Upload photos and get links
        photo_links = VendorService.upload_photos_to_drive(service, photos, vendor_id)

        return jsonify({
            "message": "Photos uploaded successfully",
            "photo_links": photo_links
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error uploading photos: {e}")
        return jsonify({"error": str(e)}), 500

@vendor_bp.route('/vendor/<int:vendor_id>/photos', methods=['GET'])
def get_vendor_photos(vendor_id):
    """
    API endpoint to retrieve all photos for a given vendor ID.
    
    Args:
        vendor_id (int): The ID of the vendor for which we are fetching photos.
    
    Returns:
        JSON: A list of photos associated with the vendor, including image ID and path.
    """
    try:
        # Query the database for images associated with the vendor ID
        images = Image.query.filter_by(vendor_id=vendor_id).all()
        
        if not images:
            return jsonify({"message": "No photos found for this vendor."}), 404

        # Prepare a list of image details
        photo_data = []
        for image in images:
            photo_data.append({
                "image_id": image.image_id,
                "path": image.path
            })

        # Return the photo data as a JSON response
        return jsonify({"photos": photo_data}), 200

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"error": str(e)}), 500

@vendor_bp.route('/bookingQueue', methods=['POST'])
def insert_to_queue():
    try:
        data = request.get_json(silent=True) or {}
        console_id = data.get('console_id')
        booking_id = data.get('booking_id')
        access_code = data.get('access_code') or data.get('accessCode')
        vendor_id = data.get('vendor_id')
        game_id = data.get('game_id')
        additional_console_ids = data.get('additional_console_ids') or []

        if not console_id:
            return jsonify({'error': 'console_id is required'}), 400
        if not booking_id and not access_code:
            return jsonify({'error': 'booking_id or access_code is required'}), 400

        payload = {
            "console_id": console_id,
            "additional_console_ids": additional_console_ids,
        }
        if booking_id:
            payload["booking_id"] = booking_id
        if access_code:
            payload["access_code"] = access_code
        if vendor_id:
            payload["vendor_id"] = vendor_id
        if game_id:
            payload["game_id"] = game_id

        resp = requests.post(
            f"{DASHBOARD_SERVICE_URL}/api/kiosk/start-session",
            json=payload,
            timeout=6,
        )
        try:
            body = resp.json()
        except Exception:
            body = {"message": resp.text}
        return jsonify(body), resp.status_code

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _emit_unlock(console_id, booking_id, start_dt, end_dt):
    """Emit unlock signal to internal WebSocket service"""
    payload = {
        "console_id": int(console_id),
        "booking_id": int(booking_id),
        "start_time": start_dt.astimezone(dt_timezone.utc).isoformat(),
        "end_time": end_dt.astimezone(dt_timezone.utc).isoformat()
    }
    headers = {
        "Content-Type": "application/json",
        "X-Idempotency-Key": f"{booking_id}:{console_id}"
    }
    try:
        requests.post(INTERNAL_WS_URL, json=payload, headers=headers, timeout=2.5)
    except Exception:
        pass

@vendor_bp.route('/bookingQueue', methods=['GET'])
def poll_queue():
    try:
        console_id = request.args.get('console_id')
        if not console_id:
            return jsonify({'error': 'Console ID required'}), 400

        queue_entry = BookingQueue.query.filter_by(console_id=console_id, status='queued').first()
        if not queue_entry:
            return jsonify({'message': 'No queued entry found'}), 204

        # Update queue status and start time
        queue_entry.status = 'started'
        queue_entry.start_time = dt.utcnow()

        vendor_id = queue_entry.vendor_id
        user_id = queue_entry.user_id
        game_id = queue_entry.game_id
        start_time = queue_entry.start_time
        end_time = queue_entry.end_time

        # ✅ Fetch relevant slots between start and end time
        slot_ids = db.session.query(Slot.id).filter(
            Slot.vendor_id == vendor_id,
            Slot.start_time >= start_time,
            Slot.end_time <= end_time
        ).all()
        slot_ids = [s.id for s in slot_ids]

        if not slot_ids:
            return jsonify({"error": "No slots found in time range"}), 404

        # ✅ Fetch all matching bookings
        bookings = Booking.query.filter(
            Booking.slot_id.in_(slot_ids),
            Booking.user_id == user_id,
            Booking.vendor_id == vendor_id,
            Booking.game_id == game_id
        ).all()

        if not bookings:
            return jsonify({"error": "No relevant bookings found"}), 404

        booking_ids = [b.id for b in bookings]

        # ✅ Dynamic table names
        console_table_name = f"VENDOR_{vendor_id}_CONSOLE_AVAILABILITY"
        booking_table_name = f"VENDOR_{vendor_id}_DASHBOARD"

        # ✅ Check console availability
        sql_check_availability = text(f"""
            SELECT is_available FROM {console_table_name}
            WHERE console_id = :console_id AND game_id = :game_id
        """)
        result = db.session.execute(sql_check_availability, {
            "console_id": console_id,
            "game_id": game_id
        }).fetchone()

        if not result:
            return jsonify({"error": "Console not found"}), 404

        if not result.is_available:
            return jsonify({"error": "Console is already in use"}), 400

        # ✅ Mark console as unavailable
        sql_update_console_status = text(f"""
            UPDATE {console_table_name}
            SET is_available = FALSE
            WHERE console_id = :console_id AND game_id = :game_id
        """)
        db.session.execute(sql_update_console_status, {
            "console_id": console_id,
            "game_id": game_id
        })

        # ✅ Update bookings to 'current' and assign console
        sql_update_bookings = text(f"""
            UPDATE {booking_table_name}
            SET book_status = 'current', console_id = :console_id
            WHERE book_id = ANY(:booking_ids) AND game_id = :game_id AND book_status = 'upcoming'
        """)
        db.session.execute(sql_update_bookings, {
            "console_id": console_id,
            "game_id": game_id,
            "booking_ids": booking_ids
        })

        db.session.commit()

        return jsonify({
            'message': 'Queued entry started and console assigned',
            'booking_ids': booking_ids,
            'user_id': user_id,
            'game_id': game_id,
            'vendor_id': vendor_id,
            'start_time': queue_entry.start_time,
            'end_time': queue_entry.end_time
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@vendor_bp.route('/bookingQueue/next-slot/check', methods=['POST'])
def kiosk_next_slot_check_proxy():
    """
    Proxy for kiosk continuation availability check.
    """
    try:
        data = request.get_json(silent=True) or {}
        vendor_id = data.get("vendor_id") or data.get("vendorId")
        if not vendor_id:
            return jsonify({"success": False, "message": "vendor_id is required"}), 400

        payload = {
            "current_booking_id": data.get("current_booking_id") or data.get("currentBookingId") or data.get("booking_id"),
            "game_id": data.get("game_id") or data.get("gameId"),
            "console_id": data.get("console_id") or data.get("consoleId"),
            "user_id": data.get("user_id") or data.get("userId"),
        }
        # Keep backward compatibility for access-code based kiosk clients.
        if data.get("access_code") or data.get("accessCode"):
            payload["access_code"] = data.get("access_code") or data.get("accessCode")

        response = requests.post(
            f"{BOOKING_SERVICE_URL}/api/kiosk/next-slot/check/vendor/{int(vendor_id)}",
            json=payload,
            timeout=8,
        )
        try:
            body = response.json()
        except Exception:
            body = {"success": False, "message": response.text}
        return jsonify(body), response.status_code
    except Exception as e:
        current_app.logger.exception("kiosk_next_slot_check_proxy failed")
        return jsonify({"success": False, "message": "Proxy error", "error": str(e)}), 500


@vendor_bp.route('/bookingQueue/next-slot/confirm', methods=['POST'])
def kiosk_next_slot_confirm_proxy():
    """
    Proxy for kiosk continuation booking confirmation.
    """
    try:
        data = request.get_json(silent=True) or {}
        vendor_id = data.get("vendor_id") or data.get("vendorId")
        if not vendor_id:
            return jsonify({"success": False, "message": "vendor_id is required"}), 400

        payload = {
            "current_booking_id": data.get("current_booking_id") or data.get("currentBookingId") or data.get("booking_id"),
            "game_id": data.get("game_id") or data.get("gameId"),
            "console_id": data.get("console_id") or data.get("consoleId"),
            "user_id": data.get("user_id") or data.get("userId"),
            "slot_id": data.get("slot_id") or data.get("slotId"),
            "paymentType": data.get("paymentType") or data.get("modeOfPayment") or "pending",
            "autoStart": bool(data.get("autoStart", True)),
            "kioskId": data.get("kioskId") or data.get("kiosk_id"),
        }
        if data.get("access_code") or data.get("accessCode"):
            payload["access_code"] = data.get("access_code") or data.get("accessCode")

        response = requests.post(
            f"{BOOKING_SERVICE_URL}/api/kiosk/next-slot/vendor/{int(vendor_id)}",
            json=payload,
            timeout=10,
        )
        try:
            body = response.json()
        except Exception:
            body = {"success": False, "message": response.text}
        if response.status_code >= 500:
            current_app.logger.error(
                "Next-slot confirm downstream failure vendor=%s status=%s payload=%s response=%s",
                vendor_id,
                response.status_code,
                payload,
                body,
            )
        return jsonify(body), response.status_code
    except Exception as e:
        current_app.logger.exception("kiosk_next_slot_confirm_proxy failed")
        return jsonify({"success": False, "message": "Proxy error", "error": str(e)}), 500


@vendor_bp.route('/accessCodeUnlock', methods=['POST'])
def unlock_with_code():
    data = request.get_json(silent=True) or {}
    access_code = data.get('access_code') or data.get('accessCode')
    console_id = data.get('console_id')
    game_id = data.get('game_id')
    vendor_id = data.get('vendor_id')
    additional_console_ids = data.get('additional_console_ids') or []

    if not access_code or not console_id:
        return jsonify({'error': 'Missing access_code or console_id'}), 400

    payload = {
        "console_id": console_id,
        "access_code": access_code,
        "additional_console_ids": additional_console_ids,
    }
    if vendor_id:
        payload["vendor_id"] = vendor_id
    if game_id:
        payload["game_id"] = game_id

    try:
        resp = requests.post(
            f"{DASHBOARD_SERVICE_URL}/api/kiosk/start-session",
            json=payload,
            timeout=6,
        )
        try:
            body = resp.json()
        except Exception:
            body = {"message": resp.text}
        return jsonify(body), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500



   # add image route

@vendor_bp.route('/vendor/<int:vendor_id>/add-image', methods=['POST'])
def upload_vendor_image(vendor_id):
    """
    Uploads an image for a vendor to Cloudinary and saves the URL in the DB, linking it to the vendor.
    Expects form-data: 'image' (file), optional 'label' (text)
    """
    
    image_file = request.files.get('image')
    

    if not image_file or image_file.filename == '':
        return jsonify({'success': False, 'message': 'No image file provided'}), 400

    vendor = Vendor.query.get(vendor_id)
    if not vendor:
        return jsonify({'success': False, 'message': 'Vendor not found'}), 404

    # Upload to Cloudinary
    upload_result = CloudinaryGameImageService.upload_game_cover_image(image_file, vendor.cafe_name)
    if not upload_result['success']:
        return jsonify({'success': False, 'message': 'Cloudinary upload failed', 'error': upload_result['error']}), 500

    # Save in DB
    new_image = Image(
        url=upload_result['url'],
        public_id=upload_result['public_id'],
        vendor_id=vendor_id,
        
    )
    db.session.add(new_image)
    db.session.commit()
    
    db.session.refresh(vendor)
    
     # Return all images to keep frontend in sync
    all_images = [{'id': img.id, 'url': img.url, 'public_id': img.public_id} for img in vendor.images]


    return jsonify({
        'success': True,
        'message': 'Vendor image uploaded and saved successfully',
        'image': {
            'id': new_image.id,
            'url': new_image.url,
            'public_id': new_image.public_id,
            
        },
        'all_images': all_images
    }), 201
    
    
#@vendor_bp.route('/vendor/<int:vendor_id>/dashboard', methods=['GET'])
#def get_vendor_dashboard_data(vendor_id):
 #   """
  #  API to retrieve vendor dashboard data - only contact info and images.
   # """
    #try:
     #   vendor = Vendor.query.get(vendor_id)
      #  if not vendor:
       #     return jsonify({'success': False, 'message': 'Vendor not found'}), 
        #
        
        #db.session.refresh(vendor)

        # Fetch all images for this vendor
        #images = [img.url for img in vendor.images]
        
        # Get contact info
        #contact_info = vendor.contact_info
        
        #response_data = {
         #   "success": True,
          #  "cafeProfile": {
           #     "name": vendor.cafe_name or "Cafe Name",
            #    "membershipStatus": "Standard Member",
             #   "website": contact_info.website if contact_info and hasattr(contact_info, 'website') else "Not Available",
              #  "email": contact_info.email if contact_info else "No Email Provided",
               # "phone": contact_info.phone if contact_info else "No Phone Provided"
            #},
           # "cafeGallery": {
            #    "images": images
           #3 }
       # }
        
       # return jsonify(response_data), 200
        
    #except Exception as e:
     #   current_app.logger.error(f"Dashboard API Error: {str(e)}")
      #  return jsonify({'success': False, 'error': 'Failed to fetch dashboard data'}), 500
    
    
@vendor_bp.route('/vendor/<int:vendor_id>/dashboard', methods=['GET'])
def get_vendor_dashboard_data(vendor_id):
    """
    API to retrieve vendor dashboard data with real document information
    """
    try:
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({'success': False, 'message': 'Vendor not found'}), 404

        # Refresh vendor object to get latest data from database
        #db.session.refresh(vendor)
        
        # Fetch all images
        images = [img.url for img in vendor.images]
        
        # Get contact info
        contact_info = vendor.contact_info
        
        # IMPORTANT: Fetch real documents from your Document model
        documents = Document.query.filter_by(vendor_id=vendor_id).all()
        verified_documents = []
        
        for doc in documents:
            verified_documents.append({
                "id": doc.id,
                "name": doc.document_type.replace('_', ' ').title(),
                "status": doc.status,
                "expiry": "No expiry",  # You can add actual expiry logic if needed
                "uploadedAt": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "documentUrl": doc.document_url,  # This is the Cloudinary URL
                "publicId": doc.public_id        # This is the Cloudinary public_id
            })
        
        response_data = {
            "success": True,
            "cafeProfile": {
                "name": vendor.cafe_name or "Cafe Name",
                "membershipStatus": "Standard Member",
                "website": contact_info.website if contact_info and hasattr(contact_info, 'website') else "Not Available",
                "email": contact_info.email if contact_info else "No Email Provided",
                "phone": contact_info.phone if contact_info else "No Phone Provided"
            },
            "cafeGallery": {
                "images": images
            },
            "verifiedDocuments": verified_documents  # Real document data
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Dashboard API Error: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to fetch dashboard data'}), 500


@vendor_bp.route('/vendor/<int:vendor_id>/delete-image/<int:image_id>', methods=['DELETE'])
def delete_vendor_image(vendor_id, image_id):
    """
    Deletes a vendor image from both Cloudinary and the database by image ID.
    """
    
    try:
        # Check if vendor exists
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({'success': False, 'message': 'Vendor not found'}), 404
        
        # Check if image exists and belongs to the vendor
        image = Image.query.filter_by(id=image_id, vendor_id=vendor_id).first()
        if not image:
            return jsonify({'success': False, 'message': 'Image not found or does not belong to this vendor'}), 404
        
        # Store image info for response
        deleted_image_info = {
            'id': image.id,
            'public_id': image.public_id,
            'url': image.url
        }
        
        # Track deletion status
        cloudinary_deleted = False
        database_deleted = False
        
        # Try to delete from Cloudinary first
        try:
            delete_result = CloudinaryGameImageService.delete_image(image.public_id)
            if delete_result['success']:
                cloudinary_deleted = True
            else:
                # Log error but continue with database deletion
                print(f"Cloudinary deletion failed for {image.public_id}: {delete_result.get('error')}")
        except Exception as cloudinary_error:
            print(f"Cloudinary deletion exception for {image.public_id}: {cloudinary_error}")
        
        # Delete from database regardless of Cloudinary result
        try:
            db.session.delete(image)
            db.session.commit()
            database_deleted = True
        except Exception as db_error:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': 'Failed to delete image from database',
                'error': str(db_error)
            }), 500
        
        # Refresh vendor to get updated images list
        db.session.refresh(vendor)
        
        # Build remaining images list
        remaining_images = []
        for img in vendor.images:
            image_url = getattr(img, "path", None) or getattr(img, "url", "") or ""
            remaining_images.append({
                'id': img.id, 
                'url': image_url, 
                'public_id': img.public_id,
                'uploaded_at': img.uploaded_at.isoformat() if img.uploaded_at else None
            })
        
        # Determine response message based on what was deleted
        if cloudinary_deleted and database_deleted:
            message = 'Image deleted successfully from both Cloudinary and database'
        elif database_deleted:
            message = 'Image deleted from database. Cloudinary deletion failed but image record removed.'
        else:
            message = 'Partial deletion - please contact support'
        
        return jsonify({
            'success': True,
            'message': message,
            'deleted_image': deleted_image_info,
            'remaining_images': remaining_images,
            'cloudinary_deleted': cloudinary_deleted,
            'database_deleted': database_deleted
        }), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error deleting image {image_id} for vendor {vendor_id}: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'An unexpected error occurred while deleting the image',
            'error': str(e)
        }), 500

@vendor_bp.route('/vendor/<int:vendor_id>/delete-image-by-url', methods=['DELETE'])
def delete_vendor_image_by_url(vendor_id):
    """
    Deletes a vendor image by URL from both Cloudinary and the database.
    """
    
    data = request.get_json()
    image_url = data.get('imageUrl')
    
    if not image_url:
        return jsonify({'success': False, 'message': 'Image URL is required'}), 400
    
    # Check if vendor exists
    vendor = Vendor.query.get(vendor_id)
    if not vendor:
        return jsonify({'success': False, 'message': 'Vendor not found'}), 404
    
    # Find image by URL
    image = Image.query.filter_by(url=image_url, vendor_id=vendor_id).first()
    if not image:
        # Try to find by path as well (since your dashboard uses path)
        image = Image.query.filter_by(path=image_url, vendor_id=vendor_id).first()
        
    if not image:
        return jsonify({'success': False, 'message': 'Image not found or does not belong to this vendor'}), 404
    
    # Delete from Cloudinary
    delete_result = CloudinaryGameImageService.delete_image(image.public_id)
    if not delete_result['success']:
        return jsonify({
            'success': False, 
            'message': 'Failed to delete image from Cloudinary', 
            'error': delete_result['error']
        }), 500
    
    # Delete from database
    db.session.delete(image)
    db.session.commit()
    
    # Refresh vendor to get updated images list
    db.session.refresh(vendor)
    
    # Return remaining images to keep frontend in sync
    remaining_images = [{'id': img.id, 'url': img.url, 'public_id': img.public_id} for img in vendor.images]
    
    return jsonify({
        'success': True,
        'message': 'Vendor image deleted successfully',
        'remaining_images': remaining_images
    }), 200
    
    
    # Add these imports at the top


# Add these routes to your vendor_bp blueprint

@vendor_bp.route('/vendor/<int:vendor_id>/send-otp', methods=['POST'])
def send_otp(vendor_id):
    """Send OTP for accessing restricted pages"""
    try:
        data = request.get_json()
        page_type = data.get('page_type')  # 'bank_transfer' or 'payout_history'
        
        if page_type not in ['bank_transfer', 'payout_history']:
            return jsonify({
                'success': False, 
                'message': 'Invalid page type'
            }), 400
        
        result = OTPService.send_otp(vendor_id, page_type)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in send_otp: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Internal server error'
        }), 500

@vendor_bp.route('/vendor/<int:vendor_id>/verify-otp', methods=['POST'])
def verify_otp(vendor_id):
    """Verify OTP for accessing restricted pages"""
    try:
        data = request.get_json()
        page_type = data.get('page_type')
        otp = data.get('otp')
        
        if not page_type or not otp:
            return jsonify({
                'success': False, 
                'message': 'Page type and OTP are required'
            }), 400
        
        if page_type not in ['bank_transfer', 'payout_history']:
            return jsonify({
                'success': False, 
                'message': 'Invalid page type'
            }), 400
        
        result = OTPService.verify_otp(vendor_id, page_type, otp)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        current_app.logger.error(f"Error in verify_otp: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Internal server error'
        }), 500

@vendor_bp.route('/vendor/<int:vendor_id>/check-verification', methods=['GET'])
def check_verification(vendor_id):
    """Check if vendor is already verified for a page"""
    try:
        page_type = request.args.get('page_type')
        
        if not page_type or page_type not in ['bank_transfer', 'payout_history']:
            return jsonify({
                'success': False, 
                'message': 'Invalid page type'
            }), 400
        
        is_verified = OTPService.is_verified(vendor_id, page_type)
        
        return jsonify({
            'success': True,
            'is_verified': is_verified
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error in check_verification: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Internal server error'
        }), 500

@vendor_bp.route('/vendor/<int:vendor_id>/updateSlot', methods=['POST'])
def update_slot(vendor_id):
    """
    Update slot windows for ALL AvailableGame (console types) for ALL future dates of the given weekday.
    Also upserts day-wise configuration into vendor_day_slot_config.

    Payload:
    {
      "start_time": "09:00 AM",   // required, 12h format
      "end_time":   "11:00 PM",   // required, 12h format
      "slot_duration": 30,        // required minutes
      "day": "sun"                // required, one of mon..sun or full day name
      "is_enabled": true,         // optional, default true
      "is_24_hours": false,       // optional, if true uses 00:00-00:00 full-day window
      "window_days": 60,          // optional, rolling window for generation (1..365)
      "start_date": "2026-03-31"  // optional YYYY-MM-DD, useful for EOM extension
    }
    """
    try:
        payload = request.get_json(silent=True) or {}

        # Validate required fields
        start_time_str = payload.get("start_time")
        end_time_str   = payload.get("end_time")
        slot_duration  = payload.get("slot_duration")
        day_key        = payload.get("day")
        is_enabled     = bool(payload.get("is_enabled", True))
        is_24_hours    = bool(payload.get("is_24_hours", False))
        window_days    = payload.get("window_days", FUTURE_WINDOW_DAYS)
        start_date_raw = payload.get("start_date")

        if not slot_duration or not day_key:
            return jsonify({"message": "slot_duration and day are required"}), 400

        try:
            slot_duration = int(slot_duration)
        except (TypeError, ValueError):
            return jsonify({"message": "slot_duration must be an integer (minutes)"}), 400
        if slot_duration < 15 or slot_duration > 240:
            return jsonify({"message": "slot_duration must be between 15 and 240 minutes"}), 400

        try:
            window_days = int(window_days)
        except (TypeError, ValueError):
            return jsonify({"message": "window_days must be an integer between 1 and 365"}), 400
        if window_days < 1 or window_days > 365:
            return jsonify({"message": "window_days must be between 1 and 365"}), 400

        if start_date_raw:
            try:
                start_anchor = dt.strptime(str(start_date_raw), "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"message": "start_date must be YYYY-MM-DD"}), 400
        else:
            start_anchor = date.today()

        # Parse times (12h/24h mode)
        if is_24_hours:
            start_time = dtime(0, 0)
            end_time = dtime(0, 0)
        else:
            if not start_time_str or not end_time_str:
                return jsonify({"message": "start_time and end_time are required unless is_24_hours=true"}), 400
            start_time = parse_time_flexible(start_time_str)
            end_time = parse_time_flexible(end_time_str)
            if not start_time or not end_time:
                return jsonify({"message": "start_time/end_time must be in 'HH:MM AM/PM' or 'HH:MM' format"}), 400

        # Validate/normalize day
        day_key = normalize_day_key(day_key)
        if not day_key:
            return jsonify({"message": "Invalid day. Use mon..sun or full day name"}), 400
        target_weekday = WEEKDAY_MAP[day_key]

        # Validate vendor has console types configured.
        game_count = db.session.query(func.count(AvailableGame.id)).filter(AvailableGame.vendor_id == vendor_id).scalar() or 0
        if game_count <= 0:
            return jsonify({"message": "No console types (AvailableGame) found for vendor"}), 404

        # Upsert vendor_day_slot_config
        opening_str_for_config = start_time.strftime("%I:%M %p")
        closing_str_for_config = end_time.strftime("%I:%M %p")

        # Try update, else insert (simple upsert)
        update_result = db.session.execute(
            text("""
                UPDATE vendor_day_slot_config
                   SET opening_time = :opening_time,
                       closing_time = :closing_time,
                       slot_duration = :slot_duration
                 WHERE vendor_id = :vendor_id
                   AND day = :day
            """),
            {
                "vendor_id": vendor_id,
                "day": day_key,
                "opening_time": opening_str_for_config,
                "closing_time": closing_str_for_config,
                "slot_duration": slot_duration
            }
        )
        if update_result.rowcount == 0:
            db.session.execute(
                text("""
                    INSERT INTO vendor_day_slot_config (vendor_id, day, opening_time, closing_time, slot_duration)
                    VALUES (:vendor_id, :day, :opening_time, :closing_time, :slot_duration)
                """),
                {
                    "vendor_id": vendor_id,
                    "day": day_key,
                    "opening_time": opening_str_for_config,
                    "closing_time": closing_str_for_config,
                    "slot_duration": slot_duration
                }
            )

        # Keep opening_days in sync with operating-hours toggle
        od_update = db.session.execute(
            text("""
                UPDATE opening_days
                   SET is_open = :is_open
                 WHERE vendor_id = :vendor_id
                   AND lower(substr(day,1,3)) = :day
            """),
            {"vendor_id": vendor_id, "day": day_key, "is_open": is_enabled}
        )
        if od_update.rowcount == 0:
            db.session.execute(
                text("""
                    INSERT INTO opening_days (vendor_id, day, is_open)
                    VALUES (:vendor_id, :day, :is_open)
                """),
                {"vendor_id": vendor_id, "day": day_key, "is_open": is_enabled}
            )

        # Build target dates for this weekday.
        end_window = start_anchor + timedelta(days=window_days)
        target_dates = []
        cur = start_anchor
        while cur <= end_window:
            if cur.weekday() == target_weekday:
                target_dates.append(cur)
            cur += timedelta(days=1)

        if not target_dates:
            return jsonify({"message": "No matching dates found in the configured window"}), 400

        blocks = _generate_blocks(start_anchor, start_time, end_time, slot_duration)
        games = AvailableGame.query.filter_by(vendor_id=vendor_id).all()
        result = _apply_slot_rows_for_day(vendor_id, games, target_dates, blocks, is_enabled)
        db.session.commit()
        return jsonify({
            "message": "Day-wise slot configuration saved and applied",
            "vendor_id": vendor_id,
            "day": day_key,
            "is_enabled": is_enabled,
            "is_24_hours": is_24_hours,
            "window_start": start_anchor.isoformat(),
            "future_window_days": window_days,
            "updated_days": result["updated_days"],
            "inserted_rows": result["inserted_rows"]
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[update_slot] Error for vendor {vendor_id}: {e}")
        return jsonify({"message": "Failed to update slot configuration", "error": str(e)}), 500


@vendor_bp.route('/vendor/<int:vendor_id>/extendSlotWindow', methods=['POST'])
def extend_slot_window(vendor_id):
    """
    Extend slot inventory horizon without regenerating existing dates.
    Payload:
    {
      "start_date": "2026-04-01",  // optional, defaults to tomorrow
      "window_days": 60             // optional, defaults to 60
    }
    """
    try:
        payload = request.get_json(silent=True) or {}
        window_days = payload.get("window_days", 60)
        try:
            window_days = int(window_days)
        except (TypeError, ValueError):
            return jsonify({"message": "window_days must be an integer between 1 and 365"}), 400
        if window_days < 1 or window_days > 365:
            return jsonify({"message": "window_days must be between 1 and 365"}), 400

        raw_start = payload.get("start_date")
        if raw_start:
            try:
                start_date = dt.strptime(str(raw_start), "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"message": "start_date must be YYYY-MM-DD"}), 400
        else:
            start_date = date.today() + timedelta(days=1)

        end_date = start_date + timedelta(days=window_days)
        VendorService.extend_vendor_slot_window(vendor_id, start_date, end_date)
        db.session.commit()

        return jsonify({
            "message": "Slot window extended successfully",
            "vendor_id": vendor_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "window_days": window_days
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[extend_slot_window] Error for vendor {vendor_id}: {e}")
        return jsonify({"message": "Failed to extend slot window", "error": str(e)}), 500
