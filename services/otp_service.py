import random
import string
from flask import current_app
from flask_mail import Message
from db.extensions import mail, redis_client, db
from models.vendor import Vendor
from models.vendorAccount import VendorAccount
import logging
from threading import Thread
from datetime import datetime

logger = logging.getLogger(__name__)


# CRITICAL FIX: Add this helper function for async email sending
def send_async_email(app, msg):
    """Send email asynchronously in background thread"""
    with app.app_context():
        try:
            mail.send(msg)
            app.logger.info("Email sent successfully in background")
        except Exception as e:
            app.logger.error(f"Failed to send email asynchronously: {str(e)}")


class OTPService:
    OTP_EXPIRY_SECONDS = 300  # 5 minutes
    VERIFICATION_EXPIRY_SECONDS = 1800  # 30 minutes
    
    @staticmethod
    def generate_otp(length=6):
        """Generate a random numeric OTP"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def send_otp(vendor_id, page_type):
        """
        Send OTP to vendor's email for accessing restricted pages
        OPTIMIZED: Returns immediately, email sent in background
        """
        try:
            # OPTIMIZED: Use select specific columns only - faster query
            vendor_data = db.session.query(
                Vendor.id,
                Vendor.cafe_name,
                VendorAccount.email,
                VendorAccount.name
            ).join(VendorAccount, Vendor.account_id == VendorAccount.id)\
             .filter(Vendor.id == vendor_id)\
             .first()
        
            if not vendor_data:
                logger.error(f"Vendor {vendor_id} not found")
                return {'success': False, 'message': 'Vendor not found'}
        
            if not vendor_data.email:
                logger.error(f"Email not found for vendor {vendor_id}")
                return {'success': False, 'message': 'Vendor email not found in account'}
            
            vendor_email = vendor_data.email
            vendor_name = vendor_data.name or vendor_data.cafe_name or 'Vendor'
            cafe_name = vendor_data.cafe_name or 'your cafe'
            
            # Generate OTP
            otp = OTPService.generate_otp()
            
            # OPTIMIZED: Store OTP in Redis with 5-minute expiry
            redis_key = f'vendor_otp:{vendor_id}:{page_type}'
            redis_client.setex(redis_key, OTPService.OTP_EXPIRY_SECONDS, otp)
            
            # Prepare email content
            page_name = "Bank Transfer" if page_type == "bank_transfer" else "Payout History"
            
            msg = Message(
                subject=f'OTP for {page_name} Access - HashForGamers',
                recipients=[vendor_email],
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            msg.html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #2563eb; margin: 0;">HashForGamers</h1>
                        <p style="color: #666; margin: 5px 0;">Gaming Cafe Dashboard</p>
                    </div>
                    
                    <h2 style="color: #2563eb;">Security Verification Required</h2>
                    <p>Hello <strong>{vendor_name}</strong>,</p>
                    
                    <p>You are trying to access the <strong>{page_name}</strong> section for <strong>{cafe_name}</strong>. For security purposes, please verify your identity with the OTP below:</p>
                    
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 10px; text-align: center; margin: 30px 0;">
                        <p style="color: white; margin: 0 0 10px 0; font-size: 16px;">Your OTP Code</p>
                        <h1 style="color: white; font-size: 42px; margin: 0; letter-spacing: 8px; font-weight: bold;">{otp}</h1>
                    </div>
                    
                    <div style="background-color: #fef3c7; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b; margin: 25px 0;">
                        <p style="margin: 0; color: #92400e;"><strong>Important Security Information:</strong></p>
                        <ul style="margin: 10px 0; color: #92400e;">
                            <li>This OTP is valid for <strong>5 minutes only</strong></li>
                            <li>Never share this OTP with anyone</li>
                            <li>HashForGamers support will never ask for your OTP</li>
                            <li>If you didn't request this access, please ignore this email</li>
                        </ul>
                    </div>
                    
                    <div style="margin: 30px 0; padding: 20px; background-color: #f8fafc; border-radius: 8px;">
                        <p style="margin: 0; font-size: 14px; color: #475569;">
                            <strong>Why do we send this OTP?</strong><br>
                            We protect sensitive areas like payment and banking information with additional security to keep your account safe.
                        </p>
                    </div>
                    
                    <hr style="margin: 30px 0; border: none; height: 1px; background-color: #e2e8f0;">
                    
                    <p style="font-size: 12px; color: #64748b; text-align: center; margin: 0;">
                        This is an automated security email from HashForGamers Dashboard.<br>
                        Please do not reply to this email. If you need assistance, contact our support team.
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.body = f"""
            HashForGamers - Security Verification Required
            
            Hello {vendor_name},
            
            You are trying to access the {page_name} section for {cafe_name}. For security purposes, please verify your identity with the OTP below:
            
            OTP: {otp}
            
            Important:
            - This OTP is valid for 5 minutes only
            - Never share this OTP with anyone
            - HashForGamers support will never ask for your OTP
            - If you didn't request this access, please ignore this email
            
            Why do we send this OTP?
            We protect sensitive areas like payment and banking information with additional security to keep your account safe.
            
            Best regards,
            HashForGamers Team
            
            ---
            This is an automated security email. Please do not reply.
            """
            
            # CRITICAL FIX: Send email asynchronously - THIS IS THE KEY!
            # The API returns immediately while email sends in background
            Thread(
                target=send_async_email,
                args=(current_app._get_current_object(), msg),
                daemon=True  # Daemon thread won't block app shutdown
            ).start()
            
            logger.info(f"OTP generation initiated for vendor {vendor_id} ({vendor_email}) for {page_type}")
            
            # Return immediately without waiting for email to complete
            return {
                'success': True, 
                'message': 'OTP sent successfully to your registered email address'
            }
            
        except Exception as e:
            logger.error(f"Error sending OTP to vendor {vendor_id}: {str(e)}", exc_info=True)
            return {
                'success': False, 
                'message': 'Failed to send OTP. Please try again later.'
            }
    
    @staticmethod
    def verify_otp(vendor_id, page_type, provided_otp):
        """
        Verify the provided OTP
        OPTIMIZED: Fast Redis lookup with proper string comparison
        """
        try:
            redis_key = f'vendor_otp:{vendor_id}:{page_type}'
            stored_otp = redis_client.get(redis_key)
            
            if not stored_otp:
                logger.warning(f"OTP not found or expired for vendor {vendor_id}, page {page_type}")
                return {'success': False, 'message': 'OTP expired or not found. Please request a new one.'}
            
            # FIXED: Proper string comparison (works with decode_responses=True)
            # If decode_responses is False, stored_otp will be bytes
            if isinstance(stored_otp, bytes):
                stored_otp = stored_otp.decode('utf-8')
            
            if provided_otp.strip() == stored_otp.strip():
                # OTP is correct, delete it from Redis
                redis_client.delete(redis_key)
                
                # Set verification flag with longer expiry (30 minutes)
                verification_key = f'vendor_verified:{vendor_id}:{page_type}'
                redis_client.setex(
                    verification_key, 
                    OTPService.VERIFICATION_EXPIRY_SECONDS, 
                    'verified'
                )
                
                logger.info(f"OTP verified successfully for vendor {vendor_id} for {page_type}")
                return {'success': True, 'message': 'OTP verified successfully'}
            else:
                logger.warning(f"Invalid OTP provided for vendor {vendor_id}, page {page_type}")
                return {'success': False, 'message': 'Invalid OTP. Please try again.'}
                
        except Exception as e:
            logger.error(f"Error verifying OTP for vendor {vendor_id}: {str(e)}", exc_info=True)
            return {'success': False, 'message': 'OTP verification failed. Please try again.'}
    
    @staticmethod
    def is_verified(vendor_id, page_type):
        """
        Check if vendor is already verified for the page
        OPTIMIZED: Instant Redis check - no database query
        """
        try:
            verification_key = f'vendor_verified:{vendor_id}:{page_type}'
            # This is INSTANT - just checks if key exists in Redis
            return redis_client.exists(verification_key) > 0
        except Exception as e:
            logger.error(f"Error checking verification status for vendor {vendor_id}: {str(e)}")
            return False
    
    @staticmethod
    def clear_verification(vendor_id, page_type):
        """Clear verification status (for logout or security purposes)"""
        try:
            verification_key = f'vendor_verified:{vendor_id}:{page_type}'
            redis_client.delete(verification_key)
            logger.info(f"Verification cleared for vendor {vendor_id}, page {page_type}")
            return True
        except Exception as e:
            logger.error(f"Error clearing verification for vendor {vendor_id}: {str(e)}")
            return False
    
    @staticmethod
    def clear_all_verification(vendor_id):
        """Clear all verification status for a vendor (for logout)"""
        try:
            # Clear verification for both pages
            for page_type in ['bank_transfer', 'payout_history']:
                verification_key = f'vendor_verified:{vendor_id}:{page_type}'
                redis_client.delete(verification_key)
            
            logger.info(f"All verification cleared for vendor {vendor_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing all verification for vendor {vendor_id}: {str(e)}")
            return False
    
    @staticmethod
    def get_verification_status(vendor_id):
        """Get verification status for all pages - FAST"""
        try:
            status = {}
            for page_type in ['bank_transfer', 'payout_history']:
                verification_key = f'vendor_verified:{vendor_id}:{page_type}'
                status[page_type] = redis_client.exists(verification_key) > 0
            
            return {'success': True, 'status': status}
        except Exception as e:
            logger.error(f"Error getting verification status for vendor {vendor_id}: {str(e)}")
            return {'success': False, 'message': 'Failed to get verification status'}
    
    @staticmethod
    def resend_otp(vendor_id, page_type):
        """
        Resend OTP (same as send_otp but with different logging)
        OPTIMIZED: Returns immediately
        """
        try:
            # Delete existing OTP if any
            redis_key = f'vendor_otp:{vendor_id}:{page_type}'
            redis_client.delete(redis_key)
            
            # Send new OTP (async)
            result = OTPService.send_otp(vendor_id, page_type)
            
            if result['success']:
                logger.info(f"OTP resent successfully to vendor {vendor_id} for {page_type}")
                return {
                    'success': True,
                    'message': 'OTP resent successfully to your registered email address'
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error resending OTP to vendor {vendor_id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': 'Failed to resend OTP. Please try again later.'
            }
    
    @staticmethod
    def get_otp_expiry(vendor_id, page_type):
        """Get remaining time for OTP expiry - FAST"""
        try:
            redis_key = f'vendor_otp:{vendor_id}:{page_type}'
            ttl = redis_client.ttl(redis_key)
            
            if ttl == -2:  # Key does not exist
                return {'success': False, 'message': 'OTP not found'}
            elif ttl == -1:  # Key exists but has no expiry
                return {'success': True, 'expires_in': -1}
            else:
                return {'success': True, 'expires_in': ttl}
                
        except Exception as e:
            logger.error(f"Error getting OTP expiry for vendor {vendor_id}: {str(e)}")
            return {'success': False, 'message': 'Failed to get OTP expiry'}
