# services/cloudinary_service.py
"""
Updated Cloudinary service for handling game cover images in 'poc' folder
Fixed: Removed invalid format="auto" parameter that was causing API errors
"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import current_app
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import time
import hashlib
import hmac

class CloudinaryGameImageService:
    """
    Service for handling game cover images
    Images are uploaded to the 'poc' folder
    """
    
    @staticmethod
    def is_cloudinary_configured():
        """Checking if Cloudinary credentials are available"""
        return all([
            current_app.config.get('CLOUDINARY_CLOUD_NAME'),
            current_app.config.get('CLOUDINARY_API_KEY'),
            current_app.config.get('CLOUDINARY_API_SECRET')
        ])
    
    @staticmethod
    def configure_cloudinary():
        """Initialize Cloudinary configuration"""
        try:
            if not CloudinaryGameImageService.is_cloudinary_configured():
                current_app.logger.warning("Cloudinary credentials not configured")
                return False
                
            cloudinary.config(
                cloud_name=current_app.config.get('CLOUDINARY_CLOUD_NAME'),
                api_key=current_app.config.get('CLOUDINARY_API_KEY'),
                api_secret=current_app.config.get('CLOUDINARY_API_SECRET')
            )
            
            current_app.logger.info("Cloudinary configured successfully for game images")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to configure Cloudinary: {str(e)}")
            return False
    
    @staticmethod
    def upload_game_cover_image(cover_image_file, game_name):
        """
        Upload game cover image to Cloudinary 'poc' folder
        """
        try:
            # Debug logging
            current_app.logger.info(f"Starting upload for game: {game_name}")
            current_app.logger.info(f"File received: {cover_image_file}")
            current_app.logger.info(f"Filename: {getattr(cover_image_file, 'filename', 'No filename')}")
            
            # Validate file input
            if not cover_image_file or cover_image_file.filename == '':
                current_app.logger.warning("No cover image file provided")
                return {
                    'success': False,
                    'error': 'No cover image file provided',
                    'url': None,
                    'public_id': None
                }
            
            # Check file size (prevent large file issues)
            try:
                cover_image_file.seek(0, 2)  # Seek to end
                file_size = cover_image_file.tell()
                cover_image_file.seek(0)  # Reset to beginning
                
                current_app.logger.info(f"File size: {file_size} bytes")
                
                # 10MB limit to prevent memory issues
                if file_size > 10 * 1024 * 1024:
                    return {
                        'success': False,
                        'error': 'File too large (max 10MB)',
                        'url': None,
                        'public_id': None
                    }
            except Exception as e:
                current_app.logger.warning(f"Could not check file size: {str(e)}")
            
            # Configure Cloudinary
            if not CloudinaryGameImageService.configure_cloudinary():
                current_app.logger.error("Cloudinary configuration failed")
                return {
                    'success': False,
                    'error': 'Cloudinary not configured',
                    'url': None,
                    'public_id': None
                }
            
            # Create safe filename and public_id
            safe_game_name = secure_filename(game_name.replace(' ', '_').lower()) if game_name else 'unknown_game'
            public_id = f"game_cover_{safe_game_name}"
            
            current_app.logger.info(f"Uploading to Cloudinary with public_id: {public_id}")
            
            # FIXED UPLOAD - Removed invalid format="auto" parameter
            upload_result = cloudinary.uploader.upload(
                cover_image_file,
                folder="POC",  # Senior's specified folder
                public_id=public_id,
                resource_type="image",
                overwrite=True,
                quality="auto:best",
                # REMOVED: format="auto" - this was causing the API error
                transformation=[
                    {
                        'width': 500,
                        'height': 750,
                        'crop': 'fit',
                        'gravity': 'center'
                    }
                ]
            )
            
            # Log the full response for debugging
            current_app.logger.info(f"Cloudinary response keys: {list(upload_result.keys())}")
            
            # Safer response parsing - check if required keys exist
            if 'secure_url' in upload_result and 'public_id' in upload_result:
                current_app.logger.info(f"Game cover uploaded successfully: {upload_result['secure_url']}")
                
                return {
                    'success': True,
                    'url': upload_result['secure_url'],
                    'public_id': upload_result['public_id'],
                    'error': None
                }
            else:
                current_app.logger.error(f"Missing required keys in Cloudinary response: {upload_result}")
                return {
                    'success': False,
                    'error': 'Invalid response from Cloudinary - missing URL or public_id',
                    'url': None,
                    'public_id': None
                }
        
        except cloudinary.exceptions.Error as ce:
            # Handle Cloudinary-specific errors
            error_msg = f"Cloudinary API error: {str(ce)}"
            current_app.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'url': None,
                'public_id': None
            }
        
        except IndexError as ie:
            # Handle the specific "list index out of range" error
            error_msg = f"Index error during upload (file processing issue): {str(ie)}"
            current_app.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'url': None,
                'public_id': None
            }
        
        except ValueError as ve:
            # Handle value errors (often related to file format)
            error_msg = f"Value error during upload (likely invalid file format): {str(ve)}"
            current_app.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'url': None,
                'public_id': None
            }
        
        except Exception as e:
            # Handle any other unexpected errors
            error_msg = f"Unexpected error uploading game cover image: {str(e)}"
            current_app.logger.error(error_msg)
            current_app.logger.error(f"Error type: {type(e).__name__}")
            return {
                'success': False,
                'error': error_msg,
                'url': None,
                'public_id': None
            }
    
    @staticmethod
    def upload_game_cover_image_simple(cover_image_file, game_name):
        """
        Ultra-simple upload method as fallback
        
        """
        try:
            current_app.logger.info(f"Using simple upload method for: {game_name}")
            
            if not cover_image_file or cover_image_file.filename == '':
                return {
                    'success': False,
                    'error': 'No cover image file provided',
                    'url': None,
                    'public_id': None
                }
            
            if not CloudinaryGameImageService.configure_cloudinary():
                return {
                    'success': False,
                    'error': 'Cloudinary not configured',
                    'url': None,
                    'public_id': None
                }
            
            # Minimal upload - just upload to poc folder with no extra parameters
            upload_result = cloudinary.uploader.upload(
                cover_image_file,
                folder="POC"
            )
            
            current_app.logger.info(f"Simple upload result keys: {list(upload_result.keys())}")
            
            return {
                'success': True,
                'url': upload_result.get('secure_url'),
                'public_id': upload_result.get('public_id'),
                'error': None
            }
            
        except Exception as e:
            error_msg = f"Simple upload error: {str(e)}"
            current_app.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'url': None,
                'public_id': None
            }
    
    @staticmethod
    def delete_game_cover_image(public_id):
        """
        Delete a game cover image from Cloudinary
        """
        try:
            if not CloudinaryGameImageService.configure_cloudinary():
                return {
                    'success': False,
                    'error': 'Cloudinary not configured'
                }
            
            result = cloudinary.uploader.destroy(public_id)
            
            if result.get('result') == 'ok':
                current_app.logger.info(f"Successfully deleted image: {public_id}")
                return {
                    'success': True,
                    'error': None
                }
            else:
                current_app.logger.warning(f"Failed to delete image: {public_id}, result: {result}")
                return {
                    'success': False,
                    'error': f'Delete failed: {result.get("result", "unknown error")}'
                }
                
        except Exception as e:
            error_msg = f"Error deleting image {public_id}: {str(e)}"
            current_app.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
            
            # In your CloudinaryGameImageService class

    @staticmethod
    def delete_image(public_id):
        """
        Delete an image from Cloudinary with manual signature generation
        """
        try:
            # Get Cloudinary credentials from environment
            api_key = os.getenv('CLOUDINARY_API_KEY')
            api_secret = os.getenv('CLOUDINARY_API_SECRET') 
            cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        
            if not all([api_key, api_secret, cloud_name]):
               return {
                'success': False,
                'error': 'Cloudinary credentials not properly configured'
            }
         # Method 1: Try simple delete first
            try:
                result = cloudinary.uploader.destroy(public_id)
            
                if result.get('result') in ['ok', 'not found']:
                   return {
                    'success': True,
                    'message': 'Image deleted successfully',
                    'result': result
                }
            except Exception as simple_error:
                print(f"Simple delete failed: {simple_error}")
                
            # Method 2: Manual API call if simple method fails
            import requests
        
            timestamp = int(time.time())
        
            # Create signature
            params_to_sign = f"public_id={public_id}&timestamp={timestamp}"
            signature = hmac.new(
            api_secret.encode('utf-8'),
            params_to_sign.encode('utf-8'),
            hashlib.sha1
            ).hexdigest()  
            
             # Prepare request data
            data = {
            'public_id': public_id,
            'timestamp': timestamp,
            'api_key': api_key,
            'signature': signature
            }  
            # Make delete request
            url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/destroy"
            response = requests.post(url, data=data)
            result = response.json()
        
            if result.get('result') in ['ok', 'not found']:
               return {
                'success': True,
                'message': 'Image deleted successfully',
                'result': result
            }
            else:
                return {
                'success': False,
                'error': f'Manual delete failed: {result}',
                'result': result
            }
            
        except Exception as e:
           print(f"Delete error: {str(e)}")
        return {
            'success': False,
            'error': f'Cloudinary deletion error: {str(e)}'
        }
               
    
       
      
    
    @staticmethod
    def upload_vendor_document(document_file, cafe_name, document_type, vendor_id):
        """
        Upload vendor documents (PDFs and other files) to Cloudinary
        """
        try:
            if not document_file or document_file.filename == '':
                return {
                    'success': False, 
                    'error': 'No document file provided', 
                    'url': None, 
                    'public_id': None
                }
                
            if not CloudinaryGameImageService.configure_cloudinary():
                return {
                    'success': False, 
                    'error': 'Cloudinary not configured', 
                    'url': None, 
                    'public_id': None
                }

            # Create organized folder structure and filename
            safe_cafe_name = secure_filename(cafe_name.replace(' ', '_').lower()) if cafe_name else 'unknown_cafe'
            folder_path = f"VENDOR_DOCUMENTS/{safe_cafe_name}_ID_{vendor_id}"
            public_id = f"{document_type}_{int(datetime.utcnow().timestamp())}"

            current_app.logger.info(f"Uploading document to Cloudinary: {folder_path}/{public_id}")
            
            # Upload document to Cloudinary
            upload_result = cloudinary.uploader.upload(
                document_file,
                folder=folder_path,
                public_id=public_id,
                resource_type="auto",
                overwrite=False,
                quality="auto:best"
            )

            if 'secure_url' in upload_result and 'public_id' in upload_result:
                current_app.logger.info(f"Document uploaded successfully: {upload_result['secure_url']}")
                return {
                    'success': True,
                    'url': upload_result['secure_url'],
                    'public_id': upload_result['public_id'],
                    'error': None
                }
            else:
                current_app.logger.error(f"Invalid Cloudinary response: {upload_result}")
                return {
                    'success': False, 
                    'error': 'Invalid Cloudinary response', 
                    'url': None, 
                    'public_id': None
                }

        except Exception as e:
            current_app.logger.error(f"Cloudinary document upload error: {str(e)}")
            return {
                'success': False, 
                'error': str(e), 
                'url': None, 
                'public_id': None
            }
            

    @staticmethod
    def upload_collaborator_product_image(image_file, product_name, collaborator_name):
        """
        Upload collaborator product image to Cloudinary under folder 'COLLABORATOR_PRODUCTS/{collaborator_name}'
        """
        try:
            if not image_file or image_file.filename == '':
                return {
                    'success': False,
                    'error': 'No image file provided',
                    'url': None,
                    'public_id': None
                }

            if not CloudinaryGameImageService.configure_cloudinary():
                return {
                    'success': False,
                    'error': 'Cloudinary not configured',
                    'url': None,
                    'public_id': None
                }

            from werkzeug.utils import secure_filename
            safe_collaborator_name = secure_filename(collaborator_name.replace(' ', '_').lower()) if collaborator_name else 'unknown_collaborator'
            safe_product_name = secure_filename(product_name.replace(' ', '_').lower()) if product_name else 'unknown_product'
            
            folder_path = f"COLLABORATOR_PRODUCTS/{safe_collaborator_name}"
            public_id = f"product_{safe_product_name}_{int(datetime.utcnow().timestamp())}"

            current_app.logger.info(f"Uploading collaborator product image to Cloudinary folder: {folder_path} with public_id: {public_id}")

            upload_result = cloudinary.uploader.upload(
                image_file,
                folder=folder_path,
                public_id=public_id,
                resource_type="image",
                overwrite=False,
                quality="auto:best",
                transformation=[
                    {
                        'width': 500,
                        'height': 500,
                        'crop': 'fit',
                        'gravity': 'center'
                    }
                ]
            )

            if 'secure_url' in upload_result and 'public_id' in upload_result:
                current_app.logger.info(f"Collaborator product image uploaded successfully: {upload_result['secure_url']}")
                return {
                    'success': True,
                    'url': upload_result['secure_url'],
                    'public_id': upload_result['public_id'],
                    'error': None
                }
            else:
                current_app.logger.error(f"Invalid response keys from Cloudinary upload: {upload_result}")
                return {
                    'success': False,
                    'error': 'Invalid response from Cloudinary - missing URL or public_id',
                    'url': None,
                    'public_id': None
                }
        
        except cloudinary.exceptions.Error as ce:
            err_msg = f"Cloudinary API error: {str(ce)}"
            current_app.logger.error(err_msg)
            return {'success': False, 'error': err_msg, 'url': None, 'public_id': None}
        
        except Exception as e:
            err_msg = f"Unexpected error uploading collaborator product image: {str(e)}"
            current_app.logger.error(err_msg)
            return {'success': False, 'error': err_msg, 'url': None, 'public_id': None}


