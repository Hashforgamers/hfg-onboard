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

from db.extensions import db
from .utils import send_email, generate_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io
from datetime import datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy import text

from sqlalchemy import and_




class VendorService:

    @staticmethod
    def onboard_vendor(data, files):
        current_app.logger.debug("Onboard Vendor Started.")
        current_app.logger.debug(f"Received data: {data}")
        current_app.logger.debug(f"Received files: {files}")
        current_app.logger.info("Logging Started")
        
        try:
            # Step 1: Create Vendor placeholder
            vendor = Vendor(
                cafe_name=data.get('cafe_name'),
                owner_name=data.get('owner_name'),
                description=data.get('description', ''),
                business_registration_id=None,  # Will be updated later
                timing_id=None  # Will be updated later
            )
            db.session.add(vendor)
            db.session.flush()  # Ensure vendor.id is generated
            current_app.logger.info(f"Vendor created with ID: {vendor.id}")

            # Step 2: Create ContactInfo
            contact_info = ContactInfo(
                email=data['contact_info']['email'],
                phone=data['contact_info']['phone'],
                parent_id=vendor.id,
                parent_type="vendor"
            )
            db.session.add(contact_info)
            db.session.flush()
            current_app.logger.info(f"ContactInfo created with ID: {contact_info.id}")

            # Step 3: Create PhysicalAddress
            physical_address = PhysicalAddress(
                address_type=data['physicalAddress']['address_type'],
                addressLine1=data['physicalAddress']['addressLine1'],
                addressLine2=data['physicalAddress']['addressLine2'],
                pincode=data['physicalAddress']['pincode'],
                state=data['physicalAddress']['state'],
                country=data['physicalAddress']['country'],
                latitude=data['physicalAddress'].get('latitude'),
                longitude=data['physicalAddress'].get('longitude'),
                parent_id=vendor.id,
                parent_type="vendor"
            )
            db.session.add(physical_address)
            db.session.flush()
            current_app.logger.info(f"PhysicalAddress created with ID: {physical_address.id}")

            # Step 4: Create BusinessRegistration
            business_registration = BusinessRegistration(
                registration_number=data['business_registration_details']['registration_number'],
                registration_date=datetime.strptime(
                    data['business_registration_details']['registration_date'], '%Y-%m-%d'
                ).date()
            )
            db.session.add(business_registration)
            db.session.flush()
            current_app.logger.info(f"BusinessRegistration created with ID: {business_registration.id}")

            # Step 5: Create Timing
            timing = Timing(
                opening_time=datetime.strptime(data['timing']['opening_time'], '%I:%M %p').time(),
                closing_time=datetime.strptime(data['timing']['closing_time'], '%I:%M %p').time(),
            )
            db.session.add(timing)
            db.session.flush()
            current_app.logger.info(f"Timing created with ID: {timing.id}")

            # Step 6: Update Vendor with business_registration and timing references
            vendor.business_registration_id = business_registration.id
            vendor.timing_id = timing.id
            db.session.flush()
            current_app.logger.info(f"Vendor updated with business_registration_id: {vendor.business_registration_id}, timing_id: {vendor.timing_id}")

            # Step 7: Create OpeningDay
            opening_days_instances = [
                OpeningDay(day=day, is_open=is_open, vendor_id=vendor.id)
                for day, is_open in data['opening_day'].items()
            ]
            db.session.add_all(opening_days_instances)
            db.session.flush()
            current_app.logger.info(f"OpeningDay instances created: {opening_days_instances}")

            # Step 8: Create Amenities
            amenities_instances = [
                Amenity(name=name, vendor_id=vendor.id) for name, available in data.get('amenities', {}).items() if available
            ]
            db.session.add_all(amenities_instances)
            db.session.flush()
            current_app.logger.info(f"Amenity instances created: {amenities_instances}")

            # Step 9: Create AvailableGames
            available_games_instances = [
                AvailableGame(
                    game_name=game_name,
                    total_slot=details['total_slot'],
                    single_slot_price=details['single_slot_price'],
                    vendor_id=vendor.id
                ) for game_name, details in data.get('available_games', {}).items()
            ]
            db.session.add_all(available_games_instances)
            db.session.flush()
            current_app.logger.info(f"AvailableGame instances created: {available_games_instances}")

            # Step 10: Create Slots
            current_app.logger.debug("Creating slots for the vendor.")
            slot_data = []
            try:
                opening_time = datetime.strptime(data['timing']['opening_time'], '%I:%M %p').time()
                closing_time = datetime.strptime(data['timing']['closing_time'], '%I:%M %p').time()

                game_slots = {
                    game_name.lower(): details["total_slot"]
                    for game_name, details in data["available_games"].items()
                }
                game_ids = {game.game_name.lower(): game.id for game in available_games_instances}

                current_time = datetime.combine(datetime.today(), opening_time)
                closing_datetime = datetime.combine(datetime.today(), closing_time)

                while current_time < closing_datetime:
                    end_time = current_time + timedelta(minutes=60)
                    if end_time > closing_datetime:
                        break

                    for game_name, total_slots in game_slots.items():
                        game_id = game_ids.get(game_name)
                        if not game_id:
                            current_app.logger.warning(f"Game '{game_name}' not found in available games.")
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
                db.session.flush()
                current_app.logger.info(f"{len(slot_data)} slots created for vendor.")
            except Exception as e:
                current_app.logger.error(f"Error creating slots: {e}")
                raise

            db.session.commit()

            # Create the vendor-specific slot table
            VendorService.create_vendor_slot_table(vendor.id)

            # Create the vendor-specific console availbility 
            VendorService.create_vendor_console_availability_table(vendor.id)

            # Create the vendor-dashboard dynamic table 
            VendorService.create_vendor_dashboard_table(vendor.id)

            #Promo Table for Dynamic Discount for Vendor
            VendorService.create_vendor_promo_table(vendor.id)
        
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
        credential_username = username
        credential_password = password
        
        # Vendor Credntial storing in DB
        password_manager = PasswordManager(
            userid=vendor.id,
            password=credential_password,
            parent_id=vendor.id,
            parent_type="vendor"
        )
        db.session.add(password_manager)
        db.session.flush()
        current_app.logger.info(f"VendorCredential instances created: {password_manager}")
    
        #  Store initial vendor status as pending verification
        vendor_status = VendorStatus(
            vendor_id=vendor.id,
            status="pending_verification"  
        )
        db.session.add(vendor_status)
        db.session.flush()
        db.session.commit()
        current_app.logger.info(f"VendorStatus instances created")

        current_app.logger.info(f"Generated credentials for vendor: {vendor.owner_name}.")
        
        # # Send Credentials via Email
        # send_email(
        #     subject='Your Vendor Account Credentials',
        #     recipients=[vendor.contact_info.email],
        #     body=f"Hello {vendor.owner_name},\n\nYour account has been created.\nUsername: {username}\nPassword: {password}\n\n With Profile status as {vendor_status.status}"
        # )
        send_email(
            subject=f"""Welcome to Hash, {vendor.owner_name} – Your Gaming Dashboard is Ready!""",
            recipients=[vendor.contact_info.email],
            body="",  # Optional: can keep plain-text fallback
            html=f"""<!DOCTYPE html>
            <html lang="en">
            <head>
            <meta charset="UTF-8">
            <title>Welcome to Hash</title>
            </head>
            <body style="font-family: 'Segoe UI', sans-serif; background-color: #f4f4f4; margin: 0; padding: 0;">
            <div style="max-width: 640px; margin: auto; background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08); overflow: hidden;">

                <div style="background: linear-gradient(to right, #000000, #550000); color: #fff; text-align: center; padding: 30px 20px;">
                <h1 style="margin: 0; font-size: 24px;">Welcome to Hash</h1>
                <div style="font-size: 14px; color: #ccc; margin-top: 10px;">Your gaming café, streamlined.</div>
                </div>

                <div style="padding: 30px; color: #333;">
                <p>Hi {vendor.owner_name},</p>
                <p>We’re thrilled 🎉 to welcome <strong>{vendor.cafe_name}</strong> to the Hash platform. Your account has been successfully onboarded and is now active.</p>

                <p>Here are your login credentials:</p>
                <div style="background-color: #f9f9f9; padding: 15px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 20px;">
                    <p style="margin: 0;"><strong>Email:</strong> {vendor.contact_info.email}</p>
                    <p style="margin: 0;"><strong>Password:</strong> {password}</p>
                    <p style="margin: 10px 0 0;">
                    <a href="https://v0-hash-landing-page-hythuqlxsue.vercel.app/login" target="_blank" style="color: #550000; text-decoration: underline;">
                        Log In to Your Dashboard
                    </a>
                    </p>
                </div>

                <p>Profile status: <strong>{vendor_status.status}</strong></p>

                <p>🔧 You can now manage bookings, consoles, track statistics, and host tournaments—all from one place.</p>
                <p>If you have any questions or need help getting started, our team is here for you!</p>
                <p style="margin-top: 30px;">Happy gaming,<br><strong>The Hash Team</strong></p>
                </div>

                <div style="text-align: center; padding: 20px; font-size: 12px; color: #888; background-color: #fafafa;">
                &copy; 2025 Hash Platform. All rights reserved.
                </div>

            </div>
            </body>
            </html>"""
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

    # @staticmethod
    # def get_all_vendors_with_status():
    #     """
    #     Retrieve all vendors with their statuses and relevant information for the salesperson dashboard.

    #     :return: List of dictionaries containing vendor information and statuses.
    #     """
    #     try:
    #         vendors_data = []

    #         results = db.session.query(
    #             Vendor.id.label('vendor_id'),
    #             Vendor.cafe_name,
    #             Vendor.owner_name,
    #             VendorStatus.status,
    #             Vendor.created_at,
    #             Vendor.updated_at,
    #             ContactInfo.email,
    #             ContactInfo.phone,
    #             PhysicalAddress.addressLine1,
    #             PhysicalAddress.addressLine2,
    #             PhysicalAddress.pincode,
    #             PhysicalAddress.state,
    #             PhysicalAddress.country,
    #             PhysicalAddress.latitude,
    #             PhysicalAddress.longitude,
    #             func.count(Document.id).label('total_documents'),
    #             func.sum(case((Document.status == 'verified', 1), else_=0)).label('verified_documents')
    #         ).join(
    #             VendorStatus, VendorStatus.vendor_id == Vendor.id
    #         ).outerjoin(
    #             Document, Document.vendor_id == Vendor.id
    #         ).outerjoin(
    #             ContactInfo,
    #             and_(
    #                 ContactInfo.parent_id == Vendor.id,
    #                 ContactInfo.parent_type == 'vendor'
    #             )
    #         ).outerjoin(
    #             PhysicalAddress,
    #             and_(
    #                 PhysicalAddress.parent_id == Vendor.id,
    #                 PhysicalAddress.parent_type == 'vendor',
    #                 PhysicalAddress.is_active == True
    #             )
    #         ).group_by(
    #             Vendor.id, Vendor.cafe_name, Vendor.owner_name,
    #             VendorStatus.status, Vendor.created_at, Vendor.updated_at,
    #             ContactInfo.email, ContactInfo.phone,
    #             PhysicalAddress.addressLine1, PhysicalAddress.addressLine2,
    #             PhysicalAddress.pincode, PhysicalAddress.state, PhysicalAddress.country, PhysicalAddress.latitude, PhysicalAddress.longitude
    #         ).all()

    #         for result in results:
    #             vendors_data.append({
    #                 "vendor_id": result.vendor_id,
    #                 "cafe_name": result.cafe_name,
    #                 "owner_name": result.owner_name,
    #                 "status": result.status,
    #                 "created_at": result.created_at,
    #                 "updated_at": result.updated_at,
    #                 "email": result.email,
    #                 "phone": result.phone,
    #                 "address": {
    #                     "addressLine1": result.addressLine1,
    #                     "addressLine2": result.addressLine2,
    #                     "pincode": result.pincode,
    #                     "state": result.state,
    #                     "country": result.country,
    #                     "longitude":result.longitude,
    #                     "latitude":result.latitude
    #                 },
    #                 "total_documents": result.total_documents,
    #                 "verified_documents": result.verified_documents
    #             })

    #         return {"vendors": vendors_data}

    #     except Exception as e:
    #         current_app.logger.error(f"Error in get_all_vendors_with_status: {e}")
    #         raise

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