# app/controllers.py

from flask import Blueprint, request, jsonify, current_app
from services.services import VendorService
from werkzeug.utils import secure_filename
import json
from models.document import Document

from services.utils import process_files

from models.vendor import Vendor
from models.uploadedImage import Image

from models.bookingQueue import BookingQueue
from models.booking import Booking
from models.accessBookingCode import AccessBookingCode
from db.extensions import db
from datetime import datetime
from models.transaction import Transaction
from models.slots import Slot
from pytz import timezone



vendor_bp = Blueprint('vendor', __name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_json(data, required_fields):
    """Validate the JSON data for required fields."""
    missing_fields = [field for field in required_fields if field not in data]
    return missing_fields

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

@vendor_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200

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

    # Validate required fields and log as needed
    current_app.logger.debug("Validate required fields and log as needed")
    required_fields = [
        'cafe_name', 'owner_name', 'contact_info', 'physicalAddress',
        'business_registration_details', 'document_submitted',
        'timing', 'opening_day', 'available_games'
    ]
    missing_fields = validate_json(data, required_fields)
    if missing_fields:
        current_app.logger.warning(f"Missing fields: {missing_fields}")
        return jsonify({'message': f'Missing fields: {", ".join(missing_fields)}'}), 400

    # Process files
    current_app.logger.debug("Started Processing File")
    document_types = [
        'business_registration', 'owner_identification_proof',
        'tax_identification_number', 'bank_acc_details'
    ]

    files, error_message = process_files(request, data, document_types)
    if error_message:
        current_app.logger.error(f"File processing error: {error_message}")
        return jsonify({'message': error_message}), 400

    try:
        # Onboard the vendor and manage document uploads
        current_app.logger.debug("Onboard the vendor and manage document uploads")

        current_app.logger.debug("Calling VendorService.get_drive_service()")
        drive_service = VendorService.get_drive_service()

        current_app.logger.debug("Calling VendorService.onboard_vendor(data, files)") 
        vendor = VendorService.onboard_vendor(data, files)

        current_app.logger.debug("VendorService.handle_documents({data['document_submitted']}, files={files}, drive_service={drive_service}, vendor.id={vendor.id})")
        VendorService.handle_documents(data['document_submitted'], files, drive_service, vendor.id)

        current_app.logger.debug("VendorService.generate_credentials_and_notify(vendor)")
        VendorService.generate_credentials_and_notify(vendor)

        current_app.logger.info(f"Vendor onboarded successfully: {vendor.id}")
        return jsonify({'message': 'Vendor onboarded successfully', 'vendor_id': vendor.id}), 201
    except Exception as e:
        current_app.logger.error(f"Onboarding error: {e}")
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

        # Fetch today's bookings
        today_transactions = Transaction.query.filter_by(
            user_id=user_id,
            vendor_id=vendor_id,
            booked_date=today
        ).all()

        today_booking_ids = [t.booking_id for t in today_transactions]
        if not today_booking_ids:
            return jsonify({'error': 'No bookings found for today'}), 404

        today_bookings = Booking.query.filter(Booking.id.in_(today_booking_ids)).all()
        slot_ids = {b.slot_id for b in today_bookings}
        slots = Slot.query.filter(Slot.id.in_(slot_ids)).order_by(Slot.start_time).all()

        if not slots:
            return jsonify({'error': 'No slots found'}), 404

        # Group consecutive slots
        grouped_slots = []
        current_group = [slots[0]]

        for i in range(1, len(slots)):
            prev = current_group[-1]
            curr = slots[i]
            if curr.start_time == prev.end_time:
                current_group.append(curr)
            else:
                grouped_slots.append(current_group)
                current_group = [curr]
        grouped_slots.append(current_group)

        # Look for a group that is still valid (within or recently expired)
        from datetime import datetime as dt, timedelta

        active_group = None
        for group in grouped_slots:
            group_start = dt.combine(today, group[0].start_time)
            group_end = dt.combine(today, group[-1].end_time)
            now_dt = dt.combine(today, now_time)

            if group_start <= now_dt <= group_end + timedelta(minutes=30):  # 30-min grace
                active_group = group
                break

        if not active_group:
            return jsonify({'error': 'No active or recent booking block at this time'}), 400

        merged_start = datetime.combine(today, active_group[0].start_time)
        merged_end = datetime.combine(today, active_group[-1].end_time)

        queue = BookingQueue(
            booking_id=booking_id,
            console_id=console_id,
            game_id=game_id,
            vendor_id=vendor_id,
            user_id=user_id,
            status='queued',
            start_time=merged_start,
            end_time=merged_end
        )

        db.session.add(queue)
        db.session.commit()

        return jsonify({'message': 'Queued successfully'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

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
