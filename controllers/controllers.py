# app/controllers.py

from flask import Blueprint, request, jsonify, current_app
from services.services import VendorService
from werkzeug.utils import secure_filename
import json

vendor_bp = Blueprint('vendor', __name__)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_json(data, required_fields):
    """Validate the JSON data for required fields."""
    missing_fields = [field for field in required_fields if field not in data]
    return missing_fields

def process_files(request, document_types):
    """Process uploaded files and ensure they meet requirements."""
    files = {}
    for doc_type in document_types:
        if doc_type in request.files:
            file = request.files[doc_type]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                files[doc_type] = file
            else:
                return None, f'Invalid file for {doc_type}. Only PDF allowed.'
        else:
            # Check if the document is marked as submitted but no file is provided
            if data.get('document_submitted', {}).get(doc_type, False):
                return None, f'Missing file for {doc_type}'
    return files, None

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


    files, error_message = process_files(request, document_types)
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

        current_app.logger.debug("VendorService.handle_documents(data['document_submitted'], files, drive_service, vendor.id)")
        VendorService.handle_documents(data['document_submitted'], files, drive_service, vendor.id)

        current_app.logger.debug("VendorService.generate_credentials_and_notify(vendor)")
        VendorService.generate_credentials_and_notify(vendor)

        current_app.logger.info(f"Vendor onboarded successfully: {vendor.id}")
        return jsonify({'message': 'Vendor onboarded successfully', 'vendor_id': vendor.id}), 201
    except Exception as e:
        current_app.logger.error(f"Onboarding error: {e}")
        return jsonify({'message': 'An error occurred during onboarding', 'error': str(e)}), 500