import os
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from flask import current_app
from models.vendor import Vendor
from models.document import Document
from models.contactInfo import ContactInfo
from models.physicalAddress import PhysicalAddress
from models.availableGame import AvailableGame
from models.businessRegistration import BusinessRegistration
from models.timing import Timing
from models.amenity import Amenity
from models.openingDay import OpeningDay
from models.vendorCredentials import VendorCredential
from models.vendorStatus import VendorStatus
from models.uploadedImage import Image

from db.extensions import db
from .utils import send_email, generate_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io
from datetime import datetime

from sqlalchemy import case, func


class VendorService:
    @staticmethod
    def onboard_vendor(data, files):
        current_app.logger.debug("Onboard Vendor Started.")
        current_app.logger.debug(f"Received data: {data}")
        current_app.logger.debug(f"Received files: {files}")

        try:
            # Create ContactInfo
            contact_info = ContactInfo(
                email=data['contact_info']['email'],
                phone=data['contact_info']['phone']
            )
            db.session.add(contact_info)
            db.session.commit()
            current_app.logger.info(f"ContactInfo created with ID: {contact_info.id}")

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
            current_app.logger.info(f"PhysicalAddress created with ID: {physical_address.id}")

            # Create BusinessRegistration
            business_registration = BusinessRegistration(
                registration_number=data['business_registration_details']['registration_number'],
                registration_date=datetime.strptime(
                    data['business_registration_details']['registration_date'], '%Y-%m-%d'
                ).date()
            )
            db.session.add(business_registration)
            db.session.commit()
            current_app.logger.info(f"BusinessRegistration created with ID: {business_registration.id}")

            # Create Timing
            timing = Timing(
                opening_time=datetime.strptime(data['timing']['opening_time'], '%I:%M %p').time(),
                closing_time=datetime.strptime(data['timing']['closing_time'], '%I:%M %p').time(),
            )
            db.session.add(timing)
            db.session.commit()
            current_app.logger.info(f"Timing created with ID: {timing.id}")

            # Extract opening days
            opening_days_data = [day for day, is_open in data['opening_day'].items() if is_open]
            current_app.logger.debug(f"Extracted opening days: {opening_days_data}")

            # Create Vendor instance
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
            db.session.commit()
            current_app.logger.info(f"Vendor created with ID: {vendor.id}")

            # Create Amenity instances with vendor_id
            amenities_data = data.get('amenities', [])
            amenities_instances = [Amenity(name=amenity, vendor_id=vendor.id) for amenity in amenities_data]
            current_app.logger.debug(f"Amenity instances created: {amenities_instances}")

            # Create AvailableGame instances with vendor_id
            available_games_data = data.get('available_games', {})
            available_games_instances = [
                AvailableGame(
                    game_name=game_key,
                    total_slot=game_data['total_slot'],
                    single_slot_price=game_data['single_slot_price'],
                    vendor_id=vendor.id  # Assign vendor_id
                ) for game_key, game_data in available_games_data.items()
            ]
            current_app.logger.debug(f"AvailableGame instances created: {available_games_instances}")

            # Batch add amenities and available games
            db.session.add_all(amenities_instances)
            db.session.add_all(available_games_instances)
            db.session.commit()
            current_app.logger.info("Amenities and available games added successfully.")

            # Create OpeningDay instances with vendor_id
            opening_days_instances = [
                OpeningDay(day=day, is_open=True, vendor_id=vendor.id)
                for day in opening_days_data
            ]
            db.session.add_all(opening_days_instances)
            db.session.commit()
            current_app.logger.info(f"OpeningDay instances created: {opening_days_instances}")

            return vendor
        
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error onboarding vendor: {e}")
            raise

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
        
        # Vendor Credntial storing in DB
        vendor_credential = VendorCredential(
            vendor_id=vendor.id,
            username=vendor.credential_username,
            password_hash=vendor.credential_password
        )
        db.session.add(vendor_credential)
        db.session.commit()
        current_app.logger.info(f"VendorCredential instances created: {vendor_credential}")
    
        #  Store initial vendor status as pending verification
        vendor_status = VendorStatus(
            vendor_id=vendor.id,
            status="pending_verification"  
        )
        db.session.add(vendor_status)
        db.session.commit()
        current_app.logger.info(f"VendorStatus instances created: {vendor_status}")

        current_app.logger.info(f"Generated credentials for vendor: {vendor.owner_name}.")
        
        # Send Credentials via Email
        send_email(
            subject='Your Vendor Account Credentials',
            recipients=[vendor.contact_info.email],
            body=f"Hello {vendor.owner_name},\n\nYour account has been created.\nUsername: {username}\nPassword: {password}\n\n With Profile status as {vendor_status.status}"
        )

    @staticmethod
    def get_drive_service():
        """Initialize and return the Google Drive service."""
        credentials = service_account.Credentials.from_service_account_file(
            current_app.config['GOOGLE_APPLICATION_CREDENTIALS'],
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        current_app.logger.debug("Google Drive service initialized.")
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
            current_app.logger.info(f"File uploaded to Google Drive: {uploaded_file.get('webViewLink')}")
            return uploaded_file.get('webViewLink')
        except Exception as e:
            current_app.logger.error(f"Google Drive upload error: {e}")
            raise Exception(f"Failed to upload {doc_type} to Google Drive.")

    @staticmethod
    def get_unverified_documents(vendor_id):
        """Fetch all unverified documents for the specified vendor."""
        try:
            # Query to fetch all documents with 'unverified' status for the given vendor ID
            unverified_documents = Document.query.filter_by(vendor_id=vendor_id, status='unverified').all()

            # Extract file paths and relevant information
            documents_data = [
                {
                    "id": doc.id,
                    "document_type": doc.document_type,
                    "file_path": doc.file_path,
                    "uploaded_at": doc.uploaded_at,
                    "status": doc.status
                }
                for doc in unverified_documents
            ]

            return { "data": documents_data}, 200

        except Exception as e:
            # Log the error and provide a structured error response
            current_app.logger.error(f"Error fetching unverified documents for vendor {vendor_id}: {e}")
            return {
                "status": "error",
                "message": "An error occurred while retrieving unverified documents.",
                "error": str(e)
            }, 500            

    @staticmethod
    def verify_document(document_id):
        """Mark a document as verified and set the vendor's status to active if all documents are verified."""
        try:
            # Find the document by ID and mark it as verified
            document = Document.query.get(document_id)
            if not document:
                return {"status": "error", "message": "Document not found"}, 404
            
            # Update document status
            document.status = 'verified'
            db.session.commit()
            current_app.logger.info(f"Document {document_id} marked as verified.")

            # Check if all documents for this vendor are verified
            vendor_id = document.vendor_id
            unverified_documents = Document.query.filter_by(vendor_id=vendor_id, status='unverified').count()
            
            if unverified_documents == 0:
                # If all documents are verified, set the vendor status to 'active'
                vendor_status = VendorStatus.query.filter_by(vendor_id=vendor_id).first()
                if vendor_status:
                    vendor_status.status = 'active'
                    vendor_status.updated_at = datetime.utcnow()
                    db.session.commit()
                    current_app.logger.info(f"Vendor {vendor_id} status updated to active.")
                else:
                    return {"status": "error", "message": "Vendor status record not found"}, 404

            return {"status": "success", "message": "Document verified successfully"}, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error verifying document {document_id}: {e}")
            return {
                "status": "error",
                "message": "An error occurred while verifying the document.",
                "error": str(e)
            }, 500

    @staticmethod
    def verify_documents_and_update_vendor(document_ids):
        """
        Update specified documents' status to 'verified' and set the vendor's status to 'active'
        if all documents for the vendor are verified.
        
        :param document_ids: List of document IDs to verify
        :return: Response message and status code
        """
        try:
            # Update the status of specified documents to 'verified'
            documents = Document.query.filter(Document.id.in_(document_ids)).all()
            if not documents:
                return {'message': 'No documents found with the provided IDs'}, 404

            # Track vendors whose documents are verified
            vendor_ids = {doc.vendor_id for doc in documents}
            for document in documents:
                document.status = 'verified'
            db.session.commit()

            # Check if all documents for each vendor are verified
            for vendor_id in vendor_ids:
                unverified_docs = Document.query.filter_by(vendor_id=vendor_id, status='unverified').count()
                
                # If no unverified documents remain, set the vendor status to 'active'
                if unverified_docs == 0:
                    vendor_status = VendorStatus.query.filter_by(vendor_id=vendor_id).first()
                    if vendor_status:
                        vendor_status.status = 'active'
                        vendor_status.updated_at = datetime.utcnow()
                    else:
                        # If no existing status, create a new active status for the vendor
                        vendor_status = VendorStatus(vendor_id=vendor_id, status='active')
                        db.session.add(vendor_status)
                    db.session.commit()

            return {'message': 'Documents verified and vendor status updated where applicable'}, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error verifying documents: {e}")
            return {'message': 'An error occurred while verifying documents', 'error': str(e)}, 500


    @staticmethod
    def get_all_vendors_with_status():
        """
        Retrieve all vendors with their statuses and relevant information for the salesperson dashboard.
        
        :return: List of dictionaries containing vendor information and statuses.
        """
        try:
            vendors_data = []
            
            # Updated query to use 'cafe_name' instead of 'name'
            results = db.session.query(
                Vendor.id.label('vendor_id'),
                Vendor.cafe_name.label('cafe_name'),
                Vendor.owner_name.label('owner_name'),
                VendorStatus.status.label('status'),
                Vendor.created_at.label('created_at'),
                Vendor.updated_at.label('updated_at'),
                func.count(Document.id).label('total_documents'),
                func.sum(case((Document.status == 'verified', 1), else_=0)).label('verified_documents')
            ).join(
                VendorStatus, VendorStatus.vendor_id == Vendor.id
            ).outerjoin(
                Document, Document.vendor_id == Vendor.id
            ).group_by(
                Vendor.id, VendorStatus.status
            ).all()

            # Construct response data
            for result in results:
                vendors_data.append({
                    "vendor_id": result.vendor_id,
                    "cafe_name": result.cafe_name,
                    "owner_name": result.owner_name,
                    "status": result.status,
                    "created_at": result.created_at,
                    "updated_at": result.updated_at,
                    "total_documents": result.total_documents,
                    "verified_documents": result.verified_documents
                })

            return {"vendors": vendors_data}

        except Exception as e:
            current_app.logger.error(f"Error in get_all_vendors_with_status: {e}")
            raise


    @staticmethod
    def save_image_to_db(vendor_id, image_id, path):
        """
        Save image metadata to the database.
        
        Args:
            vendor_id (int): ID of the vendor associated with the image.
            image_id (str): Google Drive file ID of the uploaded image.
            path (str): Google Drive link path 
        Returns:
            Image: The saved Image object.
        """
        image = Image(
            vendor_id=vendor_id,
            image_id=image_id,
            path=path
        )
        db.session.add(image)
        db.session.commit()
        return image


    @staticmethod
    def get_drive_service():
        """Initialize and return the Google Drive service."""
        credentials = service_account.Credentials.from_service_account_file(
            current_app.config['GOOGLE_APPLICATION_CREDENTIALS'],
            scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        current_app.logger.debug("Google Drive service initialized.")
        return service

    @staticmethod
    def upload_photo_to_drive(service, photo, vendor_id, cnt):
        """Upload a single photo to Google Drive and return the file link."""
        photo_content = photo.read()
        filename = f"{vendor_id}_{secure_filename(photo.filename)}_{cnt}"
        file_metadata = {
            'name': filename,
            'parents': [current_app.config['GOOGLE_DRIVE_FOLDER_ID']],
            'mimeType': photo.mimetype
        }
        
        # Ensure MediaIoBaseUpload is correctly instantiated
        media = MediaIoBaseUpload(io.BytesIO(photo_content), mimetype=photo.mimetype)

        try:
            uploaded_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            # Log the entire response to check if 'id' is present
            current_app.logger.debug(f"Uploaded file response: {uploaded_file}")
            current_app.logger.info(f"Photo uploaded to Google Drive: {uploaded_file.get('webViewLink')}")
            
            # Save photo metadata in the database
            VendorService.save_image_to_db(
                vendor_id=vendor_id,
                image_id=uploaded_file.get('id'),
                path=uploaded_file.get('webViewLink')
            )
            current_app.logger.debug(f"Upload Completed: {uploaded_file}")
            return uploaded_file.get('webViewLink')
        except Exception as e:
            current_app.logger.error(f"Google Drive upload error for {photo.filename}: {e}")
            raise Exception(f"Failed to upload photo {photo.filename} to Google Drive.")

    @staticmethod
    def upload_photos_to_drive(service, photos, vendor_id):
        """Upload multiple photos to Google Drive and return their file links."""
        photo_links = []
        cnt=0
        for photo in photos:
            link = VendorService.upload_photo_to_drive(service, photo, vendor_id, cnt)
            cnt=cnt+1
            photo_links.append(link)
        return photo_links
