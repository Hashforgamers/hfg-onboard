# services/otp_service.py

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


# CRITICAL: Async email sender function
def send_async_email(app, msg):
    """Send email asynchronously in background thread"""
    with app.app_context():
        try:
            mail.send(msg)
            app.logger.info("✅ Email sent successfully in background")
        except Exception as e:
            app.logger.error(f"❌ Failed to send email asynchronously: {str(e)}")


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
        Send OTP to vendor's email - OPTIMIZED FOR SPEED
        Returns immediately while email sends in background
        """
        start_time = datetime.now()
        
        try:
            # OPTIMIZED: Quick database query - only fetch needed fields
            vendor_data = db.session.query(
                Vendor.id,
                Vendor.cafe_name,
                VendorAccount.email,
                VendorAccount.name
            ).join(VendorAccount, Vendor.account_id == VendorAccount.id)\
             .filter(Vendor.id == vendor_id)\
             .first()
        
            if not vendor_data:
                logger.error(f"❌ Vendor {vendor_id} not found")
                return {'success': False, 'message': 'Vendor not found'}
        
            if not vendor_data.email:
                logger.error(f"❌ Email not found for vendor {vendor_id}")
                return {'success': False, 'message': 'Vendor email not found in account'}
            
            vendor_email = vendor_data.email
            vendor_name = vendor_data.name or vendor_data.cafe_name or 'Vendor'
            cafe_name = vendor_data.cafe_name or 'your cafe'
            
            # Generate OTP
            otp = OTPService.generate_otp()
            
            # Store OTP in Redis with 5-minute expiry
            redis_key = f'vendor_otp:{vendor_id}:{page_type}'
            redis_client.setex(redis_key, OTPService.OTP_EXPIRY_SECONDS, otp)
            
            # Prepare email
            page_name = "Bank Transfer" if page_type == "bank_transfer" else "Payout History"
            
            msg = Message(
                subject=f'🔐 OTP for {page_name} Access - HashForGamers',
                recipients=[vendor_email],
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            msg.html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h1 style="color: #2563eb; margin: 0;">🎮 HashForGamers</h1>
                        <p style="color: #666; margin: 5px 0;">Gaming Cafe Dashboard</p>
                    </div>
                    
                    <h2 style="color: #2563eb;">🔐 Security Verification Required</h2>
                    <p>Hello <strong>{vendor_name}</strong>,</p>
                    
                    <p>You are trying to access the <strong>{page_name}</strong> section for <strong>{cafe_name}</strong>. For security purposes, please verify your identity with the OTP below:</p>
                    
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 25px; border-radius: 10px; text-align: center; margin: 30px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <p style="color: white; margin: 0 0 10px 0; font-size: 16px;">Your OTP Code</p>
                        <h1 style="color: white; font-size: 42px; margin: 0; letter-spacing: 8px; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.2);">{otp}</h1>
                    </div>
                    
                    <div style="background-color: #fef3c7; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b; margin: 25px 0;">
                        <p style="margin: 0; color: #92400e;"><strong>⚠️ Important Security Information:</strong></p>
                        <ul style="margin: 10px 0; color: #92400e;">
                            <li>This OTP is valid for <strong>5 minutes only</strong></li>
                            <li>Never share this OTP with anyone</li>
                            <li>HashForGamers support will never ask for your OTP</li>
                            <li>If you didn't request this access, please ignore this email</li>
                        </ul>
                    </div>
                    
                    <div style="margin: 30px 0; padding: 20px; background-color: #f8fafc; border-radius: 8px;">
                        <p style="margin: 0; font-size: 14px; color: #475569;">
                            <strong>🛡️ Why do we send this OTP?</strong><br>
                            We protect sensitive areas like payment and banking information with additional security to keep your account safe.
                        </p>
                    </div>
                    
                    <hr style="margin: 30px 0; border: none; height: 1px; background-color: #e2e8f0;">
                    
                    <p style="font-size: 12px; color: #64748b; text-align: center; margin: 0;">
                        This is an automated security email from HashForGamers Dashboard.<br>
                        Please do not reply to this email. If you need assistance, contact our support team.
                    </p>
                    
                    <div style="text-align: center; margin-top: 20px;">
                        <p style="font-size: 10px; color: #94a3b8;">© 2025 HashForGamers. All rights reserved.</p>
                    </div>
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
            
            # CRITICAL: Send email asynchronously in background thread
            # This allows the API to return immediately (50-100ms instead of 1500-3000ms)
            Thread(
                target=send_async_email,
                args=(current_app._get_current_object(), msg),
                daemon=True
            ).start()
            
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"✅ OTP generated for vendor {vendor_id} ({vendor_email}) for {page_type} in {elapsed:.2f}ms")
            
            # Return immediately without waiting for email
            return {
                'success': True, 
                'message': 'OTP sent successfully to your registered email address'
            }
            
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"❌ Error sending OTP to vendor {vendor_id} (took {elapsed:.2f}ms): {str(e)}", exc_info=True)
            return {
                'success': False, 
                'message': 'Failed to send OTP. Please try again later.'
            }
    
    @staticmethod
    def verify_otp(vendor_id, page_type, provided_otp):
        """Verify the provided OTP - FAST"""
        start_time = datetime.now()
        
        try:
            redis_key = f'vendor_otp:{vendor_id}:{page_type}'
            stored_otp = redis_client.get(redis_key)
            
            if not stored_otp:
                logger.warning(f"⚠️  OTP not found or expired for vendor {vendor_id}, page {page_type}")
                return {'success': False, 'message': 'OTP expired or not found. Please request a new one.'}
            
            # Handle bytes vs string (if decode_responses is False)
            if isinstance(stored_otp, bytes):
                stored_otp = stored_otp.decode('utf-8')
            
            if provided_otp.strip() == stored_otp.strip():
                # OTP is correct - delete it and set verification flag
                redis_client.delete(redis_key)
                
                # Mark as verified for 30 minutes
                verification_key = f'vendor_verified:{vendor_id}:{page_type}'
                redis_client.setex(
                    verification_key, 
                    OTPService.VERIFICATION_EXPIRY_SECONDS, 
                    'verified'
                )
                
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(f"✅ OTP verified for vendor {vendor_id} for {page_type} in {elapsed:.2f}ms")
                return {'success': True, 'message': 'OTP verified successfully'}
            else:
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                logger.warning(f"⚠️  Invalid OTP for vendor {vendor_id}, page {page_type} (took {elapsed:.2f}ms)")
                return {'success': False, 'message': 'Invalid OTP. Please try again.'}
                
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"❌ Error verifying OTP for vendor {vendor_id} (took {elapsed:.2f}ms): {str(e)}", exc_info=True)
            return {'success': False, 'message': 'OTP verification failed. Please try again.'}
    
    @staticmethod
    def is_verified(vendor_id, page_type):
        """
        Check if vendor is already verified - INSTANT
        Just checks Redis - no database query
        """
        try:
            verification_key = f'vendor_verified:{vendor_id}:{page_type}'
            is_verified = redis_client.exists(verification_key) > 0
            
            logger.debug(f"{'✅' if is_verified else '❌'} Verification check for vendor {vendor_id}, {page_type}: {is_verified}")
            return is_verified
            
        except Exception as e:
            logger.error(f"❌ Error checking verification for vendor {vendor_id}: {str(e)}")
            return False
    
    @staticmethod
    def clear_verification(vendor_id, page_type):
        """Clear verification status"""
        try:
            verification_key = f'vendor_verified:{vendor_id}:{page_type}'
            redis_client.delete(verification_key)
            logger.info(f"🗑️  Verification cleared for vendor {vendor_id}, page {page_type}")
            return True
        except Exception as e:
            logger.error(f"❌ Error clearing verification for vendor {vendor_id}: {str(e)}")
            return False
    
    @staticmethod
    def clear_all_verification(vendor_id):
        """Clear all verification status for a vendor (for logout)"""
        try:
            for page_type in ['bank_transfer', 'payout_history']:
                verification_key = f'vendor_verified:{vendor_id}:{page_type}'
                redis_client.delete(verification_key)
            
            logger.info(f"🗑️  All verification cleared for vendor {vendor_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error clearing all verification for vendor {vendor_id}: {str(e)}")
            return False
    
    @staticmethod
    def resend_otp(vendor_id, page_type):
        """Resend OTP"""
        try:
            # Delete existing OTP
            redis_key = f'vendor_otp:{vendor_id}:{page_type}'
            redis_client.delete(redis_key)
            
            # Send new OTP
            result = OTPService.send_otp(vendor_id, page_type)
            
            if result['success']:
                logger.info(f"🔄 OTP resent to vendor {vendor_id} for {page_type}")
                return {
                    'success': True,
                    'message': 'OTP resent successfully to your registered email address'
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"❌ Error resending OTP to vendor {vendor_id}: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': 'Failed to resend OTP. Please try again later.'
            }
