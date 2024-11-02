# app/services.py

import os
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from flask import current_app
from models.vendor import Vendor
from models.document import Document
from models.contactInfo import ContactInfo
from models.physicalAddress import PhysicalAddress
from models.availableGame import AvailableGame  # Add this line
from models.businessRegistration import BusinessRegistration
from models.timing import Timing
from models.amenity import Amenity
from models.openingDay import OpeningDay

from db.extensions import db
from .utils import send_email, generate_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io
from datetime import datetime

class VendorService:
    @staticmethod
    def onboard_vendor(data, files):
        current_app.logger.debug(f"Onboard Vendor Started ")
        current_app.logger.debug(f"data {data}")
        current_app.logger.debug(f"files {files}")

        # Create ContactInfo
        contact_info = ContactInfo(
            email=data['contact_info']['email'],
            phone=data['contact_info']['phone']
        )
        db.session.add(contact_info)
        db.session.commit()  # Commit to get the ID

        # Create PhysicalAddress
        physical_address = PhysicalAddress(
            address_type=data['physicalAddress']['address_type'],
            addressLine1=data['physicalAddress']['addressLine1'],
            addressLine2=data['physicalAddress']['addressLine2'],
            pincode=data['physicalAddress']['pincode'],
            state=data['physicalAddress']['state'],
            country=data['physicalAddress']['country'],
            latitude=data['physicalAddress'].get('latitude'),
            longitude=data['physicalAddress'].get('longitude')
        )
        db.session.add(physical_address)
        db.session.commit()

        # Create BusinessRegistration
        business_registration = BusinessRegistration(
            registration_number=data['business_registration_details']['registration_number'],
            registration_date=datetime.strptime(
                data['business_registration_details']['registration_date'], '%Y-%m-%d'
            ).date()
        )
        db.session.add(business_registration)
        db.session.commit()

        # Create Timing
        timing = Timing(
            opening_time=datetime.strptime(data['timing']['opening_time'], '%I:%M %p').time(),
            closing_time=datetime.strptime(data['timing']['closing_time'], '%I:%M %p').time(),
        )
        db.session.add(timing)
        db.session.commit()

        # Extract opening days and create instances
        opening_days_data = [day for day, is_open in data['opening_day'].items() if is_open]

        # Create Vendor instance
        amenities_data = data.get('amenities', [])
        available_games_data = data.get('available_games', [])

        # Create Vendor instance without amenities first to get the vendor ID
        vendor = Vendor(
            cafe_name=data.get('cafe_name'),
            owner_name=data.get('owner_name'),
            description=data.get('description', ''),
            contact_info_id=contact_info.id,
            physical_address_id=physical_address.id,
            business_registration_id=business_registration.id,
            timing_id=timing.id,
        )

        db.session.add(vendor)
        db.session.commit()  # Commit to generate vendor ID

        # Create Amenity instances with vendor_id
        amenities_instances = [Amenity(name=amenity, vendor_id=vendor.id) for amenity in amenities_data]
        current_app.logger.debug(f"amenities_instances {amenities_instances}")

        # Create AvailableGame instances without vendor_id
        available_games_instances = [
            AvailableGame(
                game_name=game_key,
                total_slot=game_data['total_slot'],
                single_slot_price=game_data['single_slot_price'],
                vendor_id=vendor.id  # Assign vendor_id
            ) for game_key, game_data in available_games_data.items()
        ]

        # Add amenities and available games to the session
        db.session.add_all(amenities_instances)
        db.session.add_all(available_games_instances)
        db.session.commit()  # Commit to save both amenities and available games

        # Create OpeningDay instances with vendor_id
        opening_days_instances = []
        for day in opening_days_data:
            opening_day = OpeningDay(
                day=day,
                is_open=True,
                vendor_id=vendor.id  # Set vendor_id here
            )
            opening_days_instances.append(opening_day)

        # Add all opening days to the session and commit
        db.session.add_all(opening_days_instances)
        db.session.commit()  # Final commit for opening days

        return vendor

    @staticmethod
    def handle_documents(documents, files, drive_service, vendor_id):
        for doc_type, submitted in documents.items():
            if submitted and doc_type in files:
                file = files[doc_type]
                try:
                    drive_file_link = VendorService.upload_to_drive(drive_service, file, doc_type, vendor_id)
                    document = Document(
                        vendor_id=vendor_id,
                        document_type=doc_type,
                        file_path=drive_file_link
                    )
                    db.session.add(document)
                    current_app.logger.debug(f"Document {doc_type} uploaded successfully for vendor {vendor_id}")
                except Exception as e:
                    current_app.logger.error(f"Error handling document {doc_type} for vendor {vendor_id}: {e}")
                    raise
        db.session.commit()

    @staticmethod
    def generate_credentials_and_notify(vendor):
        """Generate credentials for the vendor and send them via email."""
        username, password = generate_credentials()
        vendor.credential_username = username
        vendor.credential_password = generate_password_hash(password)
        db.session.commit()
    
        current_app.logger.error(f"subject: Your Vendor Account Credentials,  recipients:{vendor.contact_info.email}, body : Hello {vendor.owner_name},\n\nYour account has been created.\nUsername: {username}\nPassword: {password}\n\nPlease login and activate your profile.")
        
        # Send Credentials via Email
        # send_email(
        #     subject='Your Vendor Account Credentials',
        #     recipients=[vendor.contact_info.email],
        #     body=f"Hello {vendor.owner_name},\n\nYour account has been created.\nUsername: {username}\nPassword: {password}\n\nPlease login and activate your profile."
        # )

    @staticmethod
    def get_drive_service():
        """Initialize and return the Google Drive service."""
        credentials = service_account.Credentials.from_service_account_file(
            current_app.config['GOOGLE_APPLICATION_CREDENTIALS'],
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        return service

    @staticmethod
    def upload_to_drive(service, file, doc_type, vendor_id):
        """Upload a file to Google Drive and return the file link."""
        file_content = file.read()
        filename = f"{vendor_id}_{secure_filename(file.filename)}"
        file_metadata = {
            'name': filename,
            'parents': [current_app.config['GOOGLE_DRIVE_FOLDER_ID']],
            'mimeType': 'application/pdf'
        }
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/pdf')
        
        try:
            uploaded_file = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
            return uploaded_file.get('webViewLink')
        except Exception as e:
            current_app.logger.error(f"Google Drive upload error: {e}")
            raise Exception(f"Failed to upload {doc_type} to Google Drive.")
