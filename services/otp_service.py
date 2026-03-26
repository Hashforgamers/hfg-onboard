# services/otp_service.py

import random
import string
from flask import current_app
from flask_mail import Message
from db.extensions import mail, redis_client, db
from models.vendor import Vendor
from models.vendorAccount import VendorAccount
from services.email_template import build_hfg_email_html
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
                subject=f'OTP for {page_name} Access - Hash For Gamers',
                recipients=[vendor_email],
                sender=current_app.config['MAIL_DEFAULT_SENDER']
            )
            
            otp_html = f"""
            <p style="margin:0 0 12px 0;color:#e5e7eb;">Hello <strong>{vendor_name}</strong>,</p>
            <p style="margin:0 0 14px 0;color:#cbd5e1;line-height:1.7;">
                You are trying to access <strong>{page_name}</strong> for <strong>{cafe_name}</strong>.
                Please verify with the OTP below.
            </p>
            <div style="background:#0a1f45;border:1px solid #1d4ed8;border-radius:10px;padding:18px;text-align:center;margin:16px 0;">
                <div style="color:#93c5fd;font-size:13px;margin-bottom:6px;">One-Time Password</div>
                <div style="color:#ffffff;font-size:36px;letter-spacing:8px;font-weight:700;">{otp}</div>
            </div>
            <div style="background:#2b170a;border:1px solid #7c2d12;border-radius:8px;padding:12px;color:#fcd34d;line-height:1.65;">
                <strong>Important:</strong>
                <ul style="margin:8px 0 0 18px;padding:0;">
                    <li>This OTP is valid for 5 minutes.</li>
                    <li>Never share this OTP with anyone.</li>
                    <li>Hash For Gamers support will never ask for your OTP.</li>
                    <li>If you did not request this, you can ignore this email.</li>
                </ul>
            </div>
            <p style="margin:14px 0 0 0;color:#94a3b8;font-size:12px;">
                This is an automated security email from Hash For Gamers dashboard.
            </p>
            """
            msg.html = build_hfg_email_html(
                subject=msg.subject,
                content_html=otp_html,
                preview_text=f"Your OTP for {page_name} is {otp}",
            )
            
            msg.body = f"""
HashForGamers - Security Verification Required

Hello {vendor_name},

You are trying to access the {page_name} section for {cafe_name}. For security purposes, please verify your identity with the OTP below:

OTP: {otp}

Important:
- This OTP is valid for 5 minutes only
- Never share this OTP with anyone
- Hash For Gamers support will never ask for your OTP
- If you didn't request this access, please ignore this email

Why do we send this OTP?
We protect sensitive areas like payment and banking information with additional security to keep your account safe.

Best regards,
Hash For Gamers Team

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
