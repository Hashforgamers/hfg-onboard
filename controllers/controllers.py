# app/controllers.py

from flask import Blueprint, request, jsonify, current_app
from services.services import VendorService
from werkzeug.utils import secure_filename
import json
from services.cloudinary_services import CloudinaryGameImageService
from models.document import Document

from services.utils import process_files

from models.vendor import Vendor
from models.uploadedImage import Image

from models.bookingQueue import BookingQueue
from models.booking import Booking
from models.accessBookingCode import AccessBookingCode
from db.extensions import db
from services.otp_service import OTPService
from models.transaction import Transaction
from models.availableGame import AvailableGame
from models.slots import Slot
from models.vendorDaySlotConfig import VendorDaySlotConfig


from sqlalchemy import text
from models.timing import Timing

import uuid, requests

from pytz import timezone
from datetime import datetime, timedelta, date, time as dtime
from datetime import timezone as dt_timezone  # ✅ add this import near the top


INTERNAL_WS_URL = "https://hfg-dashboard-h9qq.onrender.com/api/internal/ws/unlock"


vendor_bp = Blueprint('vendor', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx'}

WEEKDAY_MAP = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6
}

# Adjust this window as needed (e.g., 365 for a year)
FUTURE_WINDOW_DAYS = 180

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
    """
    Save document information to database (fixed for your Document model)
    """
    try:
        for doc_type, doc_info in document_urls.items():
            # Check if document was submitted
            if document_submitted.get(doc_type, False):
                new_document = Document(
                    vendor_id=vendor_id,
                    document_type=doc_type,
                    document_url=doc_info['url'],
                    public_id=doc_info['public_id'],
                    uploaded_at=datetime.utcnow(),
                    status='unverified'  # Use 'status' instead of 'is_verified'
                )
                db.session.add(new_document)
        
        db.session.commit()
        current_app.logger.info(f"Saved {len(document_urls)} documents for vendor {vendor_id}")
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving documents to database: {str(e)}")
        raise e

    """
    Save document information to database
    """
    try:
        for doc_type, doc_info in document_urls.items():
            # Check if document was submitted
            if document_submitted.get(doc_type, False):
                new_document = Document(
                    vendor_id=vendor_id,
                    document_type=doc_type,
                    document_url=doc_info['url'],
                    public_id=doc_info['public_id'],
                    status="unverified",  # Initially not verified
                    uploaded_at=datetime.utcnow()
                )
                db.session.add(new_document)
                db.session.commit()
        current_app.logger.info(f"Saved {len(document_urls)} documents for vendor {vendor_id}")
        
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
        return datetime.strptime(date_str, format_str)
    except ValueError as e:
        current_app.logger.error(f"Error parsing date '{date_str}' with format '{format_str}': {e}")
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error parsing date '{date_str}': {e}")
        return None

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

    # Extract vendor_account_email from contact_info
    if 'contact_info' in data and data['contact_info'].get('email'):
        data['vendor_account_email'] = data['contact_info']['email']
        current_app.logger.debug(f"Set vendor_account_email: {data['vendor_account_email']}")

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
            'addressLine2': '',
            'pincode': address_data.get('zipCode', ''),
            'state': address_data.get('state', ''),
            'country': address_data.get('country', ''),
            'latitude': None,
            'longitude': None
        }
        data['physicalAddress'] = transformed_address
        current_app.logger.debug(f"Transformed address data: {data['physicalAddress']}")

    # Transform business_registration_details
    if 'business_registration_details' in data:
        reg_data = data['business_registration_details']
        if 'registration_date' not in reg_data:
            reg_data['registration_date'] = data.get('opening_day', datetime.now().strftime('%Y-%m-%d'))
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
    API to retrieve all vendors with their statuses and relevant information for the salesperson dashboard.
    """
    try:
        response_data = VendorService.get_all_gaming_cafe()
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
        data = request.get_json()
        console_id = data.get('console_id')
        game_id = data.get('game_id')
        vendor_id = data.get('vendor_id')
        booking_id = data.get('booking_id')

        if not all([console_id, game_id, vendor_id, booking_id]):
            return jsonify({'error': 'Missing fields'}), 400

        booking = Booking.query.filter_by(id=booking_id).first()
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        user_id = booking.user_id

        ist = timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        today = now_ist.date()
        now_time = now_ist.time()

        today_transactions = Transaction.query.filter_by(
            user_id=user_id, vendor_id=vendor_id, booked_date=today
        ).all()

        today_booking_ids = [t.booking_id for t in today_transactions]
        if not today_booking_ids:
            return jsonify({'error': 'No bookings found for today'}), 404

        today_bookings = Booking.query.filter(Booking.id.in_(today_booking_ids)).all()
        slot_ids = {b.slot_id for b in today_bookings}
        slots = Slot.query.filter(Slot.id.in_(slot_ids)).order_by(Slot.start_time).all()
        if not slots:
            return jsonify({'error': 'No slots found'}), 404

        # group consecutive
        grouped_slots, current_group = [], [slots[0]]
        for i in range(1, len(slots)):
            prev, curr = current_group[-1], slots[i]
            if curr.start_time == prev.end_time:
                current_group.append(curr)
            else:
                grouped_slots.append(current_group); current_group = [curr]
        grouped_slots.append(current_group)

        from datetime import datetime as dt, timedelta
        now_dt = dt.combine(today, now_time)
        active_group = None
        for group in grouped_slots:
            group_start = dt.combine(today, group[0].start_time)
            group_end = dt.combine(today, group[-1].end_time)
            if group_start <= now_dt <= group_end + timedelta(minutes=30):
                active_group = group; break
        if not active_group:
            return jsonify({'error': 'No active or recent booking block at this time'}), 400

        merged_start = datetime.combine(today, active_group[0].start_time)
        merged_end = datetime.combine(today, active_group[-1].end_time)

        # Idempotency: avoid duplicate queue rows per booking/console within same window
        existing = BookingQueue.query.filter_by(
            booking_id=booking_id, console_id=console_id, status='queued'
        ).first()
        if existing:
            # still emit unlock if first one might have been lost
            _emit_unlock(console_id, booking_id, merged_start, merged_end)
            return jsonify({'message': 'Already queued; unlock re-sent'}), 200

        queue = BookingQueue(
            booking_id=booking_id, console_id=console_id, game_id=game_id,
            vendor_id=vendor_id, user_id=user_id, status='queued',
            start_time=merged_start, end_time=merged_end
        )
        db.session.add(queue)
        db.session.commit()

        _emit_unlock(console_id, booking_id, merged_start, merged_end)
        return jsonify({'message': 'Queued and unlock sent'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def _emit_unlock(console_id, booking_id, start_dt, end_dt):
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
        queue_entry.start_time = datetime.utcnow()

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


@vendor_bp.route('/accessCodeUnlock', methods=['POST'])
def unlock_with_code():
    data = request.get_json()
    access_code = data.get('access_code')
    console_id = data.get('console_id')
    game_id = data.get('game_id')
    vendor_id = data.get('vendor_id')

    if not access_code or not console_id:
        return jsonify({'error': 'Missing access_code or console_id'}), 400

    entry = AccessBookingCode.query.filter_by(access_code=access_code).first()
    if not entry:
        return jsonify({'error': 'Invalid access code'}), 404

    booking = entry.booking

    queue = BookingQueue(
        booking_id=booking.id,
        user_id=booking.user_id,
        game_id=booking.game_id,
        vendor_id=vendor_id,
        console_id=console_id,
        status='started',
        start_time=datetime.utcnow()
    )
    db.session.add(queue)
    db.session.commit()

    return jsonify({'message': 'Booking started via access code'}), 200



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
      "day": "sun"                // required, one of mon..sun
    }
    """
    try:
        payload = request.get_json(silent=True) or {}

        # Validate required fields
        start_time_str = payload.get("start_time")
        end_time_str   = payload.get("end_time")
        slot_duration  = payload.get("slot_duration")
        day_key        = payload.get("day")

        if not start_time_str or not end_time_str or not slot_duration or not day_key:
            return jsonify({"message": "start_time, end_time, slot_duration, and day are required"}), 400

        # Parse times (12h format)
        try:
            start_time = datetime.strptime(start_time_str, "%I:%M %p").time()
            end_time   = datetime.strptime(end_time_str, "%I:%M %p").time()
        except ValueError:
            return jsonify({"message": "start_time/end_time must be in 'HH:MM AM/PM' format"}), 400

        # Validate day
        day_key = str(day_key).strip().lower()
        if day_key not in WEEKDAY_MAP:
            return jsonify({"message": f"Invalid day '{day_key}'. Use one of mon..sun"}), 400
        target_weekday = WEEKDAY_MAP[day_key]

        # Fetch all AvailableGame for vendor (apply to all)
        games = AvailableGame.query.filter_by(vendor_id=vendor_id).all()
        if not games:
            return jsonify({"message": "No console types (AvailableGame) found for vendor"}), 404

        # Upsert vendor_day_slot_config
        opening_str_for_config = start_time.strftime("%I:%M %p")  # store same format as input
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
                "slot_duration": int(slot_duration)
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
                    "slot_duration": int(slot_duration)
                }
            )

        # Build future dates for this weekday
        today = date.today()
        end_window = today + timedelta(days=FUTURE_WINDOW_DAYS)
        target_dates = []
        cur = today
        while cur <= end_window:
            if cur.weekday() == target_weekday:
                target_dates.append(cur)
            cur += timedelta(days=1)

        if not target_dates:
            return jsonify({"message": "No matching future dates found in the configured window"}), 400

        # Generate time blocks (cross-midnight safe)
        def generate_blocks(anchor_day: date):
            start_dt = datetime.combine(anchor_day, start_time)
            end_dt   = datetime.combine(anchor_day, end_time)
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)  # cross-midnight window

            blocks = []
            cur_dt = start_dt
            while cur_dt < end_dt:
                nxt_dt = cur_dt + timedelta(minutes=int(slot_duration))
                if nxt_dt > end_dt:
                    break
                block_start_t = cur_dt.time()
                block_end_t   = (nxt_dt.time() if nxt_dt.date() == cur_dt.date()
                                 else (nxt_dt - timedelta(days=1)).time())
                blocks.append((block_start_t, block_end_t))
                cur_dt = nxt_dt
            return blocks

        updated_days = 0
        inserted_rows = 0

        for d in target_dates:
            blocks = generate_blocks(d)
            if not blocks:
                current_app.logger.warning(f"[update_slot] No blocks generated for {d} with provided times/duration.")
            else:
                # Delete existing rows for this vendor and date from the dynamic table
                db.session.execute(
                    text(f"DELETE FROM VENDOR_{vendor_id}_SLOT WHERE vendor_id = :vendor_id AND date = :d"),
                    {"vendor_id": vendor_id, "d": d}
                )

                # Rebuild per game and block
                for game in games:
                    per_block_total = int(game.total_slot or 0)
                    if per_block_total <= 0:
                        continue

                    for (st, et) in blocks:
                        # Ensure base Slot exists for this (game, start, end)
                        slot_rec = Slot.query.filter_by(
                            gaming_type_id=game.id,
                            start_time=st,
                            end_time=et
                        ).first()
                        if not slot_rec:
                            slot_rec = Slot(
                                gaming_type_id=game.id,
                                start_time=st,
                                end_time=et,
                                available_slot=per_block_total,
                                is_available=False
                            )
                            db.session.add(slot_rec)
                            db.session.flush()  # obtain slot_rec.id

                        # Insert vendor daily availability WITH vendor_id
                        db.session.execute(
                            text(f"""
                                INSERT INTO VENDOR_{vendor_id}_SLOT (vendor_id, slot_id, date, available_slot, is_available)
                                VALUES (:vendor_id, :slot_id, :date, :available_slot, :is_available)
                            """),
                            {
                                "vendor_id": vendor_id,
                                "slot_id": slot_rec.id,
                                "date": d,
                                "available_slot": per_block_total,
                                "is_available": True if per_block_total > 0 else False
                            }
                        )
                        inserted_rows += 1

                updated_days += 1

        db.session.commit()

        return jsonify({
            "message": "Day-wise slot configuration saved and applied",
            "vendor_id": vendor_id,
            "day": day_key,
            "future_window_days": FUTURE_WINDOW_DAYS,
            "updated_days": updated_days,
            "inserted_rows": inserted_rows
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[update_slot] Error for vendor {vendor_id}: {e}")
        return jsonify({"message": "Failed to update slot configuration", "error": str(e)}), 500
