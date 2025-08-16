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
from models.transaction import Transaction
from models.availableGame import AvailableGame
from models.slots import Slot
from pytz import timezone

from sqlalchemy import text
from datetime import datetime, timedelta, date, time as dtime
from models.timing import Timing

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
    #.logger.debug("Started Processing File")
    #document_types = [
#'business_registration', 'owner_identification_proof',
#'tax_identification_number', 'bank_acc_details'
#]

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
        vendor = VendorService.onboard_vendor(data, files)

        # Upload documents to Cloudinary instead of Google Drive
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

@vendor_bp.route('/vendor/<int:vendor_id>/updateSlot', methods=['POST'])
def update_slot(vendor_id):
    """
    Apply new time windows to ALL future dates of the given weekday across all games.

    Payload:
    {
      "start_time": "09:00 AM",   // required, 12h format
      "end_time": "11:00 PM",     // required, 12h format
      "slot_duration": 30,        // required minutes
      "day": "sun"                // required, one of mon..sun
    }

    Behavior:
    - For each date in [today, today + FUTURE_WINDOW_DAYS] whose weekday == day:
      - DELETE existing rows for (vendor_id, date) from VENDOR_{vendor_id}_SLOT.
      - Generate blocks between start_time and end_time (cross-midnight safe).
      - For each vendor game:
         * Ensure base Slot exists for (game_id, start_time, end_time).
         * INSERT rows into VENDOR_{vendor_id}_SLOT with vendor_id, slot_id, date, available_slot, is_available.
    """
    try:
        payload = request.get_json(silent=True) or {}

        # Required inputs
        start_time_str = payload.get("start_time")
        end_time_str   = payload.get("end_time")
        slot_duration  = payload.get("slot_duration")
        day_key        = payload.get("day")

        if not start_time_str or not end_time_str or not slot_duration or not day_key:
            return jsonify({"message": "start_time, end_time, slot_duration, and day are required"}), 400

        # Parse times in 12-hour format, e.g., "09:00 AM"
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

        # Fetch vendor games
        games = AvailableGame.query.filter_by(vendor_id=vendor_id).all()
        if not games:
            return jsonify({"message": "No games found for vendor"}), 404

        # Build all future dates that match the weekday within the configured window
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

        # Time block generator (cross-midnight safe)
        def generate_blocks(anchor_day: date):
            start_dt = datetime.combine(anchor_day, start_time)
            end_dt   = datetime.combine(anchor_day, end_time)
            if end_dt <= start_dt:
                # Handle cross-midnight by extending end to next day
                end_dt += timedelta(days=1)

            blocks = []
            cur_dt = start_dt
            while cur_dt < end_dt:
                nxt_dt = cur_dt + timedelta(minutes=int(slot_duration))
                if nxt_dt > end_dt:
                    break
                block_start_t = cur_dt.time()
                # Normalize end time to same-day clock if window crosses midnight
                block_end_t = (nxt_dt.time() if nxt_dt.date() == cur_dt.date() else (nxt_dt - timedelta(days=1)).time())
                blocks.append((block_start_t, block_end_t))
                cur_dt = nxt_dt
            return blocks

        updated_days = 0
        inserted_rows = 0

        # Clear and rebuild per target date
        for d in target_dates:
            blocks = generate_blocks(d)
            if not blocks:
                current_app.logger.warning(f"[update_slot] No blocks generated for {d} with provided times/duration.")
                continue

            # Delete existing rows scoped by vendor_id and date
            db.session.execute(
                text(f"DELETE FROM VENDOR_{vendor_id}_SLOT WHERE vendor_id = :vendor_id AND date = :d"),
                {"vendor_id": vendor_id, "d": d}
            )

            # Rebuild rows for each game and block
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

        # Commit all changes atomically (no Timing updates)
        db.session.commit()

        return jsonify({
            "message": "Slot configuration updated for all future matching days",
            "vendor_id": vendor_id,
            "day": day_key,
            "future_window_days": FUTURE_WINDOW_DAYS,
            "updated_days": updated_days,
            "inserted_rows": inserted_rows
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[update_slot] Error updating slots for vendor {vendor_id}: {e}")
        return jsonify({"message": "Failed to update slot configuration", "error": str(e)}), 500
