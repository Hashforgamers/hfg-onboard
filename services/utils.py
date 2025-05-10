# app/utils.py

import string
import random
from flask_mail import Message
from db.extensions import mail
from flask import current_app
from datetime import datetime
import re
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_credentials(length=8):
    letters = string.ascii_letters
    digits = string.digits
    username = ''.join(random.choice(letters) for i in range(6))
    password = ''.join(random.choice(letters + digits) for i in range(length))
    return username, password

def send_email(subject, recipients, body, html=None):
    msg = Message(subject, recipients=recipients)
    msg.body = body
    if html:
        msg.html = html
    current_app.logger.info(f"msg: {msg}")
    try:
        mail.send(msg)
        current_app.logger.info("Mail Sent Successfully")
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {e}")

def format_filename(vendor_name, document_name):
    """Format the filename as YYYYMMDD_<Vendor_name>_<document_name_without_space_and_in_lower_case>."""
    today = datetime.today().strftime('%Y%m%d')  # Get current date in YYYYMMDD format
    formatted_vendor_name = vendor_name.replace(" ", "_").lower()  # Convert vendor name to lowercase and replace spaces with underscores
    formatted_document_name = re.sub(r'\s+', '_', document_name).replace(" ", "_").lower()  # Replace spaces with underscores and convert to lowercase
    return f"{today}_{formatted_vendor_name}_{formatted_document_name}"


def process_files(request, data, document_types):
    """Process uploaded files and ensure they meet requirements."""
    files = {}
    for doc_type in document_types:
        if doc_type in request.files:
            file = request.files[doc_type]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Format the filename based on vendor and document type
                vendor_name = data.get('cafe_name', 'unknown_vendor')  # Assuming 'cafe_name' is the vendor name
                document_name = doc_type  # Using the document type as the document name
                formatted_filename = format_filename(vendor_name, document_name)
                file.filename = formatted_filename + '.pdf'  # Append .pdf extension after formatting
                files[doc_type] = file
            else:
                return None, f'Invalid file for {doc_type}. Only PDF allowed.'
        else:
            # Check if the document is marked as submitted but no file is provided
            if data.get('document_submitted', {}).get(doc_type, False):
                return None, f'Missing file for {doc_type}'
    return files, None
