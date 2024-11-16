import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from werkzeug.utils import secure_filename
from flask import current_app
from models import Image
from db.extensions import db

class PhotoUploader:

    @staticmethod
    def save_image_to_db(vendor_id, image_id):
        """
        Save image metadata to the database.
        
        Args:
            vendor_id (int): ID of the vendor associated with the image.
            image_id (str): Google Drive file ID of the uploaded image.
        
        Returns:
            Image: The saved Image object.
        """
        image = Image(
            vendor_id=vendor_id,
            image_id=image_id
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
    def upload_photo_to_drive(service, photo, vendor_id):
        """Upload a single photo to Google Drive and return the file link."""
        photo_content = photo.read()
        filename = f"{vendor_id}_{secure_filename(photo.filename)}"
        file_metadata = {
            'name': filename,
            'parents': [current_app.config['GOOGLE_DRIVE_FOLDER_ID']],
            'mimeType': photo.mimetype
        }
        media = MediaIoBaseUpload(io.BytesIO(photo_content), mimetype=photo.mimetype)
        
        try:
            uploaded_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            current_app.logger.info(f"Photo uploaded to Google Drive: {uploaded_file.get('webViewLink')}")
            # Save photo metadata in the database
            PhotoUploader.save_image_to_db(
                vendor_id=vendor_id,
                image_id=file_id  # This is the Google Drive file ID returned after upload
            )
            return uploaded_file.get('webViewLink')
        except Exception as e:
            current_app.logger.error(f"Google Drive upload error for {photo.filename}: {e}")
            raise Exception(f"Failed to upload photo {photo.filename} to Google Drive.")

    @staticmethod
    def upload_photos_to_drive(service, photos, vendor_id):
        """Upload multiple photos to Google Drive and return their file links."""
        photo_links = []
        for photo in photos:
            link = PhotoUploader.upload_photo_to_drive(service, photo, vendor_id)
            photo_links.append(link)
        return photo_links
