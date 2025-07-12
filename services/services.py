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
from models.passwordManager import PasswordManager
from models.vendorStatus import VendorStatus
from models.uploadedImage import Image
from models.slots import Slot
from models.vendorAccount import VendorAccount
from models.vendorPin import VendorPin

from db.extensions import db
from .utils import send_email, generate_credentials, generate_unique_vendor_pin
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io
from datetime import datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy import text

from sqlalchemy import and_
from sqlalchemy.orm import joinedload



class VendorService:

    @staticmethod
    def onboard_vendor(data, files):
        current_app.logger.debug("Onboard Vendor Started.")
        current_app.logger.debug(f"Received data: {data}")
        current_app.logger.debug(f"Received files: {files}")
        
        try:
            vendor_account = None
            vendor_account_email = data.get("vendor_account_email")
            
            if vendor_account_email:
                vendor_account = VendorAccount.query.filter_by(email=vendor_account_email).first()
                if not vendor_account:
                    vendor_account = VendorAccount(email=vendor_account_email)
                    db.session.add(vendor_account)
                    db.session.flush()
                    current_app.logger.info(f"Created new VendorAccount for {vendor_account_email}")
                else:
                    current_app.logger.info(f"Found existing VendorAccount with ID: {vendor_account.id}")

            # Step 1: Vendor creation
            vendor = Vendor(
                cafe_name=data.get("cafe_name"),
                owner_name=data.get("owner_name"),
                description=data.get("description", ""),
                business_registration_id=None,
                timing_id=None,
                account=vendor_account
            )
            db.session.add(vendor)
            db.session.flush()
            current_app.logger.info(f"Vendor created with ID: {vendor.id}")

            # Step 2: Vendor PIN
            vendor_pin = VendorPin(
                vendor_id=vendor.id,
                pin_code=generate_unique_vendor_pin()
            )
            db.session.add(vendor_pin)

            # Step 3: Contact Info
            contact = data.get("contact_info", {})
            contact_info = ContactInfo(
                email=contact.get("email"),
                phone=contact.get("phone"),
                parent_id=vendor.id,
                parent_type="vendor"
            )
            db.session.add(contact_info)

            # Step 4: Address
            address = data.get("physicalAddress", {})
            physical_address = PhysicalAddress(
                address_type=address.get("address_type"),
                addressLine1=address.get("addressLine1"),
                addressLine2=address.get("addressLine2"),
                pincode=address.get("pincode"),
                state=address.get("state"),
                country=address.get("country"),
                latitude=address.get("latitude"),
                longitude=address.get("longitude"),
                parent_id=vendor.id,
                parent_type="vendor"
            )
            db.session.add(physical_address)

            # Step 5: Business Registration
            registration = data.get("business_registration_details", {})
            business_registration = BusinessRegistration(
                registration_number=registration.get("registration_number"),
                registration_date=datetime.strptime(registration.get("registration_date"), "%Y-%m-%d").date()
            )
            db.session.add(business_registration)

            # Step 6: Timing
            opening_time = datetime.strptime(data["timing"]["opening_time"], "%I:%M %p").time()
            closing_time = datetime.strptime(data["timing"]["closing_time"], "%I:%M %p").time()

            timing = Timing(opening_time=opening_time, closing_time=closing_time)
            db.session.add(timing)

            # Step 7: Update Vendor with foreign keys
            db.session.flush()
            vendor.business_registration_id = business_registration.id
            vendor.timing_id = timing.id
            db.session.flush()

            # Step 8: Opening Days
            opening_day_data = data.get("opening_day", {})
            opening_days = [
                OpeningDay(day=day, is_open=is_open, vendor_id=vendor.id)
                for day, is_open in opening_day_data.items()
            ]
            db.session.add_all(opening_days)

            # Step 9: Amenities
            amenities = [
                Amenity(name=amenity, vendor_id=vendor.id)
                for amenity, available in data.get("amenities", {}).items() if available
            ]
            db.session.add_all(amenities)

            # Step 10: Available Games
            available_games_data = data.get("available_games", {})
            available_games_instances = [
                AvailableGame(
                    game_name=game_name,
                    total_slot=details.get("total_slot", 0),
                    single_slot_price=details.get("single_slot_price", 0),
                    vendor_id=vendor.id
                ) for game_name, details in available_games_data.items()
            ]
            db.session.add_all(available_games_instances)
            db.session.flush()

            # Step 11: Slot Creation
            current_app.logger.debug("Creating slots for the vendor.")
            try:
                game_slots = {
                    game_name.lower(): details.get("total_slot", 0)
                    for game_name, details in available_games_data.items()
                }
                game_ids = {
                    game.game_name.lower(): game.id
                    for game in available_games_instances
                }

                today = datetime.today()
                current_time = datetime.combine(today, opening_time)
                closing_datetime = datetime.combine(today, closing_time)

                # Handle 12:00 AM case (i.e., after midnight)
                if closing_datetime <= current_time:
                    closing_datetime += timedelta(days=1)

                slot_duration = data.get("slot_duration", 30)
                slot_data = []

                while current_time < closing_datetime:
                    end_time = current_time + timedelta(minutes=slot_duration)
                    if end_time > closing_datetime:
                        break

                    for game_name, total_slots in game_slots.items():
                        game_id = game_ids.get(game_name)
                        if not game_id:
                            current_app.logger.warning(f"Game '{game_name}' not found.")
                            continue

                        slot = Slot(
                            gaming_type_id=game_id,
                            start_time=current_time.time(),
                            end_time=end_time.time(),
                            available_slot=total_slots,
                            is_available=False
                        )
                        slot_data.append(slot)

                    current_time = end_time

                db.session.add_all(slot_data)
                current_app.logger.info(f"{len(slot_data)} slots created for vendor.")

            except Exception as e:
                current_app.logger.error(f"Error creating slots: {e}")
                raise

            db.session.commit()

            # Step 12: Vendor-specific table creations
            VendorService.create_vendor_slot_table(vendor.id)
            VendorService.create_vendor_console_availability_table(vendor.id)
            VendorService.create_vendor_dashboard_table(vendor.id)
            VendorService.create_vendor_promo_table(vendor.id)

            current_app.logger.info(f"Vendor onboarding completed successfully: {vendor.id}")
            return vendor

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error onboarding vendor: {e}")
            raise

    @staticmethod
    def deboard_vendor(vendor_id):
        current_app.logger.info(f"Starting deboarding process for Vendor ID: {vendor_id}")
        try:
            vendor = Vendor.query.get(vendor_id)
            if not vendor:
                raise ValueError(f"No vendor found with ID {vendor_id}")

            # Step 1: Delete related Slots (via AvailableGames)
            current_app.logger.debug("Deleting related Slots")
            Slot.query.filter(
                Slot.gaming_type_id.in_(
                    db.session.query(AvailableGame.id).filter_by(vendor_id=vendor_id)
                )
            ).delete(synchronize_session=False)

            # Step 2: Delete Available Games
            current_app.logger.debug("Deleting Available Games")
            AvailableGame.query.filter_by(vendor_id=vendor_id).delete(synchronize_session=False)

            # Step 3: Delete Amenities
            current_app.logger.debug("Deleting Amenities")
            Amenity.query.filter_by(vendor_id=vendor_id).delete(synchronize_session=False)

            # Step 4: Delete Opening Days
            current_app.logger.debug("Deleting Opening Days")
            OpeningDay.query.filter_by(vendor_id=vendor_id).delete(synchronize_session=False)

            # Step 5: Nullify foreign key references before deleting Timing and BusinessRegistration
            current_app.logger.debug("Nullifying vendor timing_id and business_registration_id")
            vendor.timing_id = None
            vendor.business_registration_id = None
            db.session.flush()

            # Step 6: Delete Timing
            current_app.logger.debug("Deleting Timing")
            if vendor.timing_id:
                Timing.query.filter_by(id=vendor.timing_id).delete(synchronize_session=False)

            # Step 7: Delete Business Registration
            current_app.logger.debug("Deleting Business Registration")
            if vendor.business_registration_id:
                BusinessRegistration.query.filter_by(id=vendor.business_registration_id).delete(synchronize_session=False)

            # Step 8: Delete Physical Address
            current_app.logger.debug("Deleting Physical Address")
            PhysicalAddress.query.filter_by(parent_id=vendor_id, parent_type="vendor").delete(synchronize_session=False)

            # Step 9: Delete Contact Info
            current_app.logger.debug("Deleting Contact Info")
            ContactInfo.query.filter_by(parent_id=vendor_id, parent_type="vendor").delete(synchronize_session=False)

            # Step 10: Delete Vendor Pin
            current_app.logger.debug("Deleting Vendor Pin")
            VendorPin.query.filter_by(vendor_id=vendor_id).delete(synchronize_session=False)

            # Step 11: Delete Vendor Documents
            current_app.logger.debug("Deleting Vendor Documents")
            Document.query.filter_by(vendor_id=vendor_id).delete(synchronize_session=False)


            # Step 12: Delete Vendor record itself
            current_app.logger.debug("Deleting Vendor record")
            db.session.delete(vendor)

            # Step 13: Drop vendor-specific dynamic tables
            VendorService.drop_vendor_slot_table(vendor_id)
            VendorService.drop_vendor_console_availability_table(vendor_id)
            VendorService.drop_vendor_dashboard_table(vendor_id)
            VendorService.drop_vendor_promo_table(vendor_id)

            db.session.commit()
            current_app.logger.info(f"Successfully deboarded vendor ID: {vendor_id}")

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Failed to deboard vendor {vendor_id}: {e}")
            raise

    @staticmethod
    def drop_vendor_slot_table(vendor_id):
        table_name = f"vendor_{vendor_id}_slot"
        db.session.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        current_app.logger.info(f"Dropped slot table: {table_name}")

    @staticmethod
    def drop_vendor_console_availability_table(vendor_id):
        table_name = f"vendor_{vendor_id}_console_availability"
        db.session.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        current_app.logger.info(f"Dropped console availability table: {table_name}")

    @staticmethod
    def drop_vendor_dashboard_table(vendor_id):
        table_name = f"vendor_{vendor_id}_dashboard"
        db.session.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        current_app.logger.info(f"Dropped dashboard table: {table_name}")

    @staticmethod
    def drop_vendor_promo_table(vendor_id):
        table_name = f"vendor_{vendor_id}_promo_detail"
        db.session.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        current_app.logger.info(f"Dropped promo table: {table_name}")



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
        """Generate credentials or link to existing ones, then notify vendor."""
        email = vendor.account.email

        # Step 1: Check if PasswordManager already exists for this email
        existing_password_manager = (
            db.session.query(PasswordManager)
            .join(Vendor, Vendor.id == PasswordManager.parent_id)
            .join(ContactInfo, Vendor.contact_info)
            .filter(ContactInfo.email == email)
            .filter(PasswordManager.parent_type == 'vendor') 
            .first()
        )

        if existing_password_manager:
            # Already has credentials — link this vendor to same account
            password_manager = existing_password_manager
            current_app.logger.info(f"Linked vendor {vendor.id} to existing credentials.")
        else:
            # Generate new credentials
            username, password = generate_credentials()
            password_manager = PasswordManager(
                userid=vendor.id,
                password=password,
                parent_id=vendor.id,
                parent_type="vendor"
            )
            db.session.add(password_manager)
            db.session.flush()
            current_app.logger.info(f"Created new credentials for vendor {vendor.id}")


        # Step 2: Create VendorStatus regardless
        vendor_status = VendorStatus(
            vendor_id=vendor.id,
            status="pending_verification"
        )
        db.session.add(vendor_status)
        db.session.flush()

        db.session.commit()


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
        Retrieve all vendors with their statuses, timing info, and relevant information for the salesperson dashboard.

        :return: List of dictionaries containing vendor information and statuses.
        """
        try:
            vendors_data = []

            results = db.session.query(
                Vendor.id.label('vendor_id'),
                Vendor.cafe_name,
                Vendor.owner_name,
                VendorStatus.status,
                Vendor.created_at,
                Vendor.updated_at,
                ContactInfo.email,
                ContactInfo.phone,
                PhysicalAddress.addressLine1,
                PhysicalAddress.addressLine2,
                PhysicalAddress.pincode,
                PhysicalAddress.state,
                PhysicalAddress.country,
                PhysicalAddress.latitude,
                PhysicalAddress.longitude,
                Timing.opening_time,
                Timing.closing_time,
                func.count(Document.id).label('total_documents'),
                func.sum(case((Document.status == 'verified', 1), else_=0)).label('verified_documents')
            ).join(
                VendorStatus, VendorStatus.vendor_id == Vendor.id
            ).join(
                Timing, Timing.id == Vendor.timing_id  # join timing table
            ).outerjoin(
                Document, Document.vendor_id == Vendor.id
            ).outerjoin(
                ContactInfo,
                and_(
                    ContactInfo.parent_id == Vendor.id,
                    ContactInfo.parent_type == 'vendor'
                )
            ).outerjoin(
                PhysicalAddress,
                and_(
                    PhysicalAddress.parent_id == Vendor.id,
                    PhysicalAddress.parent_type == 'vendor',
                    PhysicalAddress.is_active == True
                )
            ).group_by(
                Vendor.id, Vendor.cafe_name, Vendor.owner_name,
                VendorStatus.status, Vendor.created_at, Vendor.updated_at,
                ContactInfo.email, ContactInfo.phone,
                PhysicalAddress.addressLine1, PhysicalAddress.addressLine2,
                PhysicalAddress.pincode, PhysicalAddress.state, PhysicalAddress.country,
                PhysicalAddress.latitude, PhysicalAddress.longitude,
                Timing.opening_time, Timing.closing_time
            ).all()

            for result in results:
                vendors_data.append({
                    "vendor_id": result.vendor_id,
                    "cafe_name": result.cafe_name,
                    "owner_name": result.owner_name,
                    "status": result.status,
                    "created_at": result.created_at,
                    "updated_at": result.updated_at,
                    "email": result.email,
                    "phone": result.phone,
                    "address": {
                        "addressLine1": result.addressLine1,
                        "addressLine2": result.addressLine2,
                        "pincode": result.pincode,
                        "state": result.state,
                        "country": result.country,
                        "longitude": result.longitude,
                        "latitude": result.latitude
                    },
                   # Convert time to string (e.g., 'HH:MM:SS')
                    "opening_time": result.opening_time.strftime("%H:%M:%S") if result.opening_time else None,
                    "closing_time": result.closing_time.strftime("%H:%M:%S") if result.closing_time else None,
                    "total_documents": result.total_documents,
                    "verified_documents": result.verified_documents
                })

            return {"vendors": vendors_data}

        except Exception as e:
            current_app.logger.error(f"Error in get_all_vendors_with_status: {e}")
            raise

    @staticmethod
    def get_all_gaming_cafe():
        """
        Retrieve all vendors with their statuses, timing info, and amenities for the salesperson dashboard.
        """
        try:
            vendors_data = []

            # Step 1: Fetch core vendor data
            results = db.session.query(
                Vendor.id.label('vendor_id'),
                Vendor.cafe_name,
                Vendor.owner_name,
                VendorStatus.status,
                Vendor.created_at,
                Vendor.updated_at,
                ContactInfo.email,
                ContactInfo.phone,
                PhysicalAddress.addressLine1,
                PhysicalAddress.addressLine2,
                PhysicalAddress.pincode,
                PhysicalAddress.state,
                PhysicalAddress.country,
                PhysicalAddress.latitude,
                PhysicalAddress.longitude,
                Timing.opening_time,
                Timing.closing_time,
                func.count(Document.id).label('total_documents'),
                func.sum(case((Document.status == 'verified', 1), else_=0)).label('verified_documents')
            ).join(
                VendorStatus, VendorStatus.vendor_id == Vendor.id
            ).join(
                Timing, Timing.id == Vendor.timing_id
            ).outerjoin(
                Document, Document.vendor_id == Vendor.id
            ).outerjoin(
                ContactInfo,
                and_(
                    ContactInfo.parent_id == Vendor.id,
                    ContactInfo.parent_type == 'vendor'
                )
            ).outerjoin(
                PhysicalAddress,
                and_(
                    PhysicalAddress.parent_id == Vendor.id,
                    PhysicalAddress.parent_type == 'vendor',
                    PhysicalAddress.is_active == True
                )
            ).group_by(
                Vendor.id, Vendor.cafe_name, Vendor.owner_name,
                VendorStatus.status, Vendor.created_at, Vendor.updated_at,
                ContactInfo.email, ContactInfo.phone,
                PhysicalAddress.addressLine1, PhysicalAddress.addressLine2,
                PhysicalAddress.pincode, PhysicalAddress.state, PhysicalAddress.country,
                PhysicalAddress.latitude, PhysicalAddress.longitude,
                Timing.opening_time, Timing.closing_time
            ).all()

            vendor_ids = [result.vendor_id for result in results]

            # Step 2: Fetch all amenities for those vendors
            amenities = db.session.query(
                Amenity.vendor_id,
                Amenity.name,
                Amenity.available
            ).filter(Amenity.vendor_id.in_(vendor_ids)).all()

            # Step 3: Organize amenities by vendor_id
            amenities_map = {}
            for amenity in amenities:
                amenities_map.setdefault(amenity.vendor_id, []).append({
                    "name": amenity.name,
                    "available": amenity.available
                })

            # Step 4: Combine both datasets
            for result in results:
                vendors_data.append({
                    "vendor_id": result.vendor_id,
                    "cafe_name": result.cafe_name,
                    "owner_name": result.owner_name,
                    "status": result.status,
                    "created_at": result.created_at,
                    "updated_at": result.updated_at,
                    "email": result.email,
                    "phone": result.phone,
                    "address": {
                        "addressLine1": result.addressLine1,
                        "addressLine2": result.addressLine2,
                        "pincode": result.pincode,
                        "state": result.state,
                        "country": result.country,
                        "longitude": result.longitude,
                        "latitude": result.latitude
                    },
                    "opening_time": result.opening_time.strftime("%H:%M:%S") if result.opening_time else None,
                    "closing_time": result.closing_time.strftime("%H:%M:%S") if result.closing_time else None,
                    "total_documents": result.total_documents,
                    "verified_documents": result.verified_documents,
                    "amenities": amenities_map.get(result.vendor_id, [])
                })

            return {"vendors": vendors_data}

        except Exception as e:
            current_app.logger.error(f"Error in get_all_gaming_cafe: {e}")
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
    
    @staticmethod
    def create_vendor_slot_table(vendor_id):
        """Creates a table for tracking daily slot availability for a vendor."""
        table_name = f"VENDOR_{vendor_id}_SLOT"

        # Drop the table if it already exists
        db.session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))

        # Create the table
        sql_create = text(f"""
        CREATE TABLE {table_name} (
            vendor_id INT NOT NULL,
            date DATE NOT NULL,
            slot_id INT NOT NULL,
            is_available BOOLEAN NOT NULL,
            available_slot INT NOT NULL,
            PRIMARY KEY (vendor_id, date, slot_id)
        )
        """)

        db.session.execute(sql_create)
        db.session.commit()

        # Populate the table initially
        start_date = datetime.utcnow().date()
        end_date = start_date + timedelta(days=365)

        sql_insert = text(f"""
        INSERT INTO {table_name} (vendor_id, date, slot_id, is_available, available_slot)
        SELECT 
            {vendor_id}, gs.date, s.id, s.is_available, s.available_slot
        FROM 
            (SELECT generate_series(:start_date, :end_date, '1 day'::INTERVAL) AS date) gs
        CROSS JOIN slots s
        WHERE s.is_available = TRUE
        AND s.gaming_type_id IN (SELECT id FROM available_games WHERE vendor_id = :vendor_id)
        ORDER BY gs.date, s.id;
        """)

        db.session.execute(sql_insert, {"start_date": start_date, "end_date": end_date, "vendor_id": vendor_id})
        db.session.commit()

        current_app.logger.info(f"Table {table_name} created and populated successfully.")

    @staticmethod
    def create_vendor_console_availability_table(vendor_id):
        """Creates a table for tracking console availability for a vendor."""
        table_name = f"VENDOR_{vendor_id}_CONSOLE_AVAILABILITY"

        # Drop the table if it already exists
        db.session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))

        # Create the table
        sql_create = text(f"""
        CREATE TABLE {table_name} (
            vendor_id INT NOT NULL,
            console_id INT NOT NULL,
            game_id INT NOT NULL,
            is_available BOOLEAN NOT NULL,
            PRIMARY KEY (vendor_id, console_id)
        )
        """)

        db.session.execute(sql_create)
        db.session.commit()

        current_app.logger.info(f"Table {table_name} created and populated successfully.")

    
    @staticmethod
    def create_vendor_dashboard_table(vendor_id):
        """Creates a table for tracking vendor dashboard details."""
        table_name = f"VENDOR_{vendor_id}_DASHBOARD"

        # Drop the table if it already exists
        db.session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))

        # Create the table
        sql_create = text(f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                user_id INT NOT NULL,
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                date DATE NOT NULL,
                book_id INT NOT NULL,
                extra_played_time INTERVAL DEFAULT '00:00:00',
                game_id INT NOT NULL,
                game_name VARCHAR(255) NOT NULL,
                console_id INT NOT NULL,
                extra_pay_status BOOLEAN DEFAULT FALSE,
                extra_pay_trans_id VARCHAR(255) NULL,
                status BOOLEAN DEFAULT TRUE,
                book_status VARCHAR(255) NULL
            )
        """)

        db.session.execute(sql_create)
        db.session.commit()

        current_app.logger.info(f"Table {table_name} created successfully.")

    @staticmethod
    def create_vendor_promo_table(vendor_id: int):
        """Creates a vendor-specific promo detail table."""
        table_name = f"VENDOR_{vendor_id}_PROMO_DETAIL"

        # Drop the table if it already exists (optional)
        db.session.execute(text(f"DROP TABLE IF EXISTS {table_name}"))

        # Create the table with relevant fields
        sql_create = text(f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                booking_id INT NOT NULL,
                transaction_id INT NOT NULL,
                promo_code VARCHAR(50),
                discount_applied FLOAT,
                actual_price FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.session.execute(sql_create)
        db.session.commit()
        current_app.logger.info(f"Table {table_name} created successfully.")