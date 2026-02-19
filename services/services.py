# services/services.py

import os
import re  # ✅ ADDED for PIN validation
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from flask import current_app
from models.vendor import Vendor
from models.document import Document
from models.contactInfo import ContactInfo
from models.physicalAddress import PhysicalAddress
from models.availableGame import AvailableGame
from models.console import Console 
from models.hardwareSpecification import HardwareSpecification
from models.maintenanceStatus import MaintenanceStatus
from models.priceAndCost import PriceAndCost
from models.additionalDetails import AdditionalDetails
from models.businessRegistration import BusinessRegistration
from models.timing import Timing
from models.amenity import Amenity
from models.openingDay import OpeningDay
from models.vendorCredentials import VendorCredential
from models.passwordManager import PasswordManager
from models.vendorStatus import VendorStatus
from models.uploadedImage import Image
from models.slots import Slot
from models.game import Game
from models.vendorGame import VendorGame
from models.vendorAccount import VendorAccount
from models.vendorPin import VendorPin
from models.booking import Booking
from models.transaction import Transaction
from models.paymentMethod import PaymentMethod
from models.paymentVendorMap import PaymentVendorMap
from sqlalchemy import exists
from db.extensions import db
from .utils import send_email, generate_credentials, generate_unique_vendor_pin
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io
from datetime import datetime, timedelta
from flask_mail import Message
from db.extensions import mail

from sqlalchemy import case, func
from sqlalchemy import text

from sqlalchemy import and_
from sqlalchemy.orm import joinedload


class VendorService:
    
    
    @staticmethod
    def safe_strptime(date_str, format_str):
        """Safely parse date string, handling None and invalid values"""
        if date_str is None or date_str == '':
           return None
    
        if not isinstance(date_str, str):
           current_app.logger.warning(f"Date string is not str type: {type(date_str)}")
           return None
    
        try:
           return datetime.strptime(date_str, format_str)
        except ValueError as e:
            current_app.logger.error(f"Error parsing date '{date_str}' with format '{format_str}': {e}")
            return None
        except Exception as e:
            current_app.logger.error(f"Unexpected error parsing date '{date_str}': {e}")
            return None
        
    @staticmethod
    def onboard_vendor(data, files):
        current_app.logger.debug("Onboard Vendor Started.")
        current_app.logger.debug(f"Received data: {data}")
        current_app.logger.debug(f"Received files: {files}")
    
        try:
           vendor_account = None
           vendor_account_email = data.get("vendor_account_email")
        
        # Create or get VendorAccount
           if vendor_account_email:
              vendor_account = VendorAccount.query.filter_by(email=vendor_account_email).first()
              if not vendor_account:
                  vendor_account = VendorAccount(email=vendor_account_email)
                  db.session.add(vendor_account)
                  db.session.commit()  # Commit immediately to ensure it's saved
                  current_app.logger.info(f"Created and committed new VendorAccount for {vendor_account_email} with ID: {vendor_account.id}")
                
                # Verify it was saved
                  saved_account = VendorAccount.query.get(vendor_account.id)
                  if saved_account:
                     current_app.logger.info(f"VendorAccount verified saved: ID={saved_account.id}, Email={saved_account.email}")
                  else:
                     current_app.logger.error(f"VendorAccount NOT saved properly")
                     raise Exception("Failed to save VendorAccount")
              else:
                  current_app.logger.info(f"Found existing VendorAccount with ID: {vendor_account.id}")

        # Step 1: Vendor creation with explicit account_id
           vendor = Vendor(
               cafe_name=data.get("cafe_name"),
               owner_name=data.get("owner_name"),
               description=data.get("description", ""),
               business_registration_id=None,
               timing_id=None,
               account_id=vendor_account.id if vendor_account else None
           )
           db.session.add(vendor)
           db.session.flush()
           current_app.logger.info(f"Vendor created with ID: {vendor.id}, Account ID: {vendor.account_id}")

        # Verify the relationship works
           if vendor_account:
              try:
                 test_account = vendor.account  # This should work if relationship is correct
                 current_app.logger.info(f"Vendor account relationship verified: {test_account.email if test_account else 'None'}")
              except Exception as e:
                 current_app.logger.warning(f"Vendor account relationship issue: {e}")

        # ✅ UPDATED Step 2: Vendor PIN - Use provided or generate
           provided_pin = data.get("vendor_pin")
           if provided_pin and provided_pin.strip():
               # Validate PIN format
               if not re.match(r'^\d{4}$', provided_pin.strip()):
                   raise ValueError("PIN must be exactly 4 digits")
               pin_code = provided_pin.strip()
               current_app.logger.info(f"Using provided PIN for vendor {vendor.id}")
           else:
               pin_code = generate_unique_vendor_pin()
               current_app.logger.info(f"Generated PIN for vendor {vendor.id}")
           
           vendor_pin = VendorPin(
               vendor_id=vendor.id,
               pin_code=pin_code
           )
           db.session.add(vendor_pin)
           
           # ✅ ADDED: Store provided password temporarily if given
           provided_password = data.get("vendor_password")
           if provided_password and provided_password.strip():
               if len(provided_password.strip()) < 6:
                   raise ValueError("Password must be at least 6 characters")
               vendor._temp_password = provided_password.strip()  # Temporary storage
               current_app.logger.info(f"Manual password provided for vendor {vendor.id}")
           else:
               vendor._temp_password = None
               current_app.logger.info(f"Will auto-generate password for vendor {vendor.id}")

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

        # Step 5: Business Registration with safe parsing
           registration = data.get("business_registration_details", {})
           registration_date_str = registration.get("registration_date")
        
           if registration_date_str:
               registration_date_parsed = VendorService.safe_strptime(registration_date_str, "%Y-%m-%d")
               if registration_date_parsed:
                  registration_date = registration_date_parsed.date()
               else:
                   registration_date = datetime.now().date()
           else:
               registration_date = datetime.now().date()
        
           business_registration = BusinessRegistration(
                registration_number=registration.get("registration_number"),
                registration_date=registration_date
            )
           db.session.add(business_registration)

        # Step 6: Timing with safe parsing
           timing_data = data.get("timing", {})
           opening_time_str = timing_data.get("opening_time")
           closing_time_str = timing_data.get("closing_time")
        
           if not opening_time_str or not closing_time_str:
              raise ValueError("Opening time and closing time are required")
        
           opening_time_parsed = VendorService.safe_strptime(opening_time_str, "%I:%M %p")
           closing_time_parsed = VendorService.safe_strptime(closing_time_str, "%I:%M %p")
        
           if not opening_time_parsed or not closing_time_parsed:
               raise ValueError(f"Invalid time format: opening_time={opening_time_str}, closing_time={closing_time_str}")
        
           opening_time = opening_time_parsed.time()
           closing_time = closing_time_parsed.time()

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
           
                      # ✅ UPDATED Step 10.5: Create Console Records WITH Child Tables AND Link to AvailableGame
           current_app.logger.debug("Creating console records for the vendor.")
           console_brand_map = {
               'pc': 'Custom Build',
               'ps5': 'Sony',
               'xbox': 'Microsoft',
               'vr': 'Meta/Oculus'
           }
           
           console_model_map = {
               'pc': 'Gaming PC',
               'ps5': 'PlayStation 5',
               'xbox': 'Xbox Series X',
               'vr': 'Quest 2/3'
           }
           
           # ✅ Create a mapping of game_name to AvailableGame instance
           available_games_map = {game.game_name.lower(): game for game in available_games_instances}
           
           all_consoles = []
           for game_name, details in available_games_data.items():
               total_slots = details.get("total_slot", 0)
               game_type = game_name.lower()
               current_app.logger.debug(f"Creating {total_slots} consoles for game type: {game_type}")
               
               # ✅ Get the corresponding AvailableGame instance
               available_game = available_games_map.get(game_type)
               if not available_game:
                   current_app.logger.warning(f"No AvailableGame found for game_type: {game_type}")
                   continue
               
               for slot_num in range(1, total_slots + 1):
                   # Create Console
                   console = Console(
                       vendor_id=vendor.id,
                       console_number=slot_num,
                       model_number=console_model_map.get(game_type, 'Unknown'),
                       serial_number=f"{vendor.id}-{game_type.upper()}-{slot_num:03d}-{datetime.now().strftime('%Y%m%d')}",
                       brand=console_brand_map.get(game_type, 'Generic'),
                       console_type=game_type,
                       release_date=None,
                       description=f"{game_type.upper()} Console #{slot_num} for {vendor.cafe_name}"
                   )
                   db.session.add(console)
                   db.session.flush()  # Get console.id
                   
                   # ✅ LINK Console to AvailableGame (Many-to-Many)
                   available_game.consoles.append(console)
                   
                   # Create child records
                   hardware_spec = HardwareSpecification(
                       console_id=console.id,
                       processor_type="" if game_type == "pc" else None,
                       graphics_card="" if game_type == "pc" else None,
                       ram_size="" if game_type == "pc" else None,
                       storage_capacity="" if game_type == "pc" else None,
                       connectivity="" if game_type == "pc" else None,
                       console_model_type=console_model_map.get(game_type, "")
                   )
                   db.session.add(hardware_spec)
                   
                   maintenance_status = MaintenanceStatus(
                       console_id=console.id,
                       available_status="available",
                       condition="new",
                       last_maintenance=datetime.now().date(),
                       next_maintenance=(datetime.now() + timedelta(days=90)).date(),
                       maintenance_notes="Initial setup during onboarding"
                   )
                   db.session.add(maintenance_status)
                   
                   price_and_cost = PriceAndCost(
                       console_id=console.id,
                       price=0,
                       rental_price=details.get("single_slot_price", 0),
                       warranty_period="1 year",
                       insurance_status="notInsured"
                   )
                   db.session.add(price_and_cost)
                   
                   additional_details = AdditionalDetails(
                       console_id=console.id,
                       supported_games="",
                       accessories=""
                   )
                   db.session.add(additional_details)
                   
                   all_consoles.append(console)
                   
           if all_consoles:
               db.session.flush()  # Flush all changes including the association
               current_app.logger.info(f"Created {len(all_consoles)} console records with associations for vendor {vendor.id}")
           else:
               current_app.logger.warning(f"No consoles created for vendor {vendor.id}")



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
                          is_available=True
                       )
                       slot_data.append(slot)

                   current_time = end_time

                   db.session.add_all(slot_data)
                   current_app.logger.info(f"{len(slot_data)} slots created for vendor.")

           except Exception as e:
              current_app.logger.error(f"Error creating slots: {e}")
              raise

           # ✅ NEW Step 11.5: Create VendorGame entries (Link games to consoles)
           current_app.logger.debug("Creating vendor game associations for consoles.")
           try:
               # Map console_type to platform names in your Game table
               platform_mapping = {
                   'pc': 'PC',
                   'ps5': 'PlayStation 5',
                   'xbox': 'Xbox One',
                   'vr': 'PC'
               }
               
               vendor_games_created = 0
               for console in all_consoles:
                   # Get platform name for this console type
                   platform_name = platform_mapping.get(console.console_type, 'PC')
                   
                   # ✅ Query top 3 highest-rated games for this platform dynamically
                   games = Game.query.filter_by(platform=platform_name)\
                                     .order_by(Game.average_rating.desc())\
                                     .limit(3)\
                                     .all()
                   
                   if not games:
                       current_app.logger.warning(f"No games found for platform: {platform_name}, skipping console {console.id}")
                       continue
                   
                   for game in games:
                       try:
                           vendor_game = VendorGame(
                               vendor_id=vendor.id,
                               game_id=game.id,
                               console_id=console.id,
                               is_available=True
                               # ✅ NO price_per_hour - it's now a dynamic @property
                               # Price is auto-fetched from AvailableGame.single_slot_price
                               # or from active ConsolePricingOffer if exists
                           )
                           db.session.add(vendor_game)
                           vendor_games_created += 1
                           current_app.logger.debug(f"Added game '{game.name}' (ID:{game.id}) to console {console.id} ({console.console_type})")
                       except Exception as inner_e:
                           # Skip duplicates (unique constraint violation)
                           current_app.logger.debug(f"Skipping game {game.id} for console {console.id}: {inner_e}")
                           db.session.rollback()
                           continue
               
               if vendor_games_created > 0:
                   db.session.flush()
                   current_app.logger.info(f"✅ Created {vendor_games_created} vendor game associations for vendor {vendor.id}")
               else:
                   current_app.logger.warning(f"No vendor games created for vendor {vendor.id}")
                   
           except Exception as e:
               current_app.logger.error(f"Error creating vendor games: {e}")
               pass  # Don't raise - vendor can add games manually later

           db.session.commit()


        # Final verification
           if vendor_account:
               final_account = VendorAccount.query.get(vendor_account.id)
               final_vendor = Vendor.query.get(vendor.id)
               current_app.logger.info(f"FINAL VERIFICATION:")
               current_app.logger.info(f"- VendorAccount exists: {final_account is not None}")
               current_app.logger.info(f"- Vendor account_id: {final_vendor.account_id}")
               current_app.logger.info(f"- Relationship works: {final_vendor.account.email if final_vendor.account else 'NO RELATIONSHIP'}")
            
            

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

            # Step 0: Handle payment mappings, transactions and bookings
            current_app.logger.debug("Handling payment mappings, transactions and bookings for this vendor's slots")

            slot_ids_subquery = db.session.query(Slot.id).filter(
                Slot.gaming_type_id.in_(
                    db.session.query(AvailableGame.id).filter_by(vendor_id=vendor_id)
                )
            )

            # Get booking IDs first
            booking_ids = [b[0] for b in db.session.query(Booking.id).filter(
                Booking.slot_id.in_(slot_ids_subquery)
            ).all()]
            
            if booking_ids:
                # First delete payment transaction mappings for these bookings
                db.session.execute(text("""
                    DELETE FROM payment_transaction_mappings
                    WHERE transaction_id IN (
                        SELECT id FROM transactions WHERE booking_id = ANY(:booking_ids)
                    )
                """), {'booking_ids': booking_ids})

                # Then delete all transactions for this vendor
                Transaction.query.filter(
                    db.or_(
                        Transaction.booking_id.in_(booking_ids),
                        Transaction.vendor_id == vendor_id
                    )
                ).delete(synchronize_session=False)

                # Finally delete the bookings
                Booking.query.filter(Booking.id.in_(booking_ids)).delete(synchronize_session=False)

            # Step 1: Delete related Slots (via AvailableGames)
            current_app.logger.debug("Deleting related Slots")
            Slot.query.filter(
                Slot.gaming_type_id.in_(
                    db.session.query(AvailableGame.id).filter_by(vendor_id=vendor_id)
                )
            ).delete(synchronize_session=False)

            # Step 2: First delete available_game_console associations
            current_app.logger.debug("Deleting available_game_console associations")
            db.session.execute(text("""
                DELETE FROM available_game_console
                WHERE available_game_id IN (
                    SELECT id FROM available_games WHERE vendor_id = :vendor_id
                )
            """), {'vendor_id': vendor_id})

            # Step 3: Delete Available Games
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

            # Step 12: Delete Extra Service Menu Images and Menus
            current_app.logger.debug("Deleting Extra Service Menu Images")
            
            # First get menu IDs linked to this vendor's extra services
            menu_ids = [m[0] for m in db.session.execute(text("""
                SELECT m.id FROM extra_service_menus m
                JOIN extra_service_categories c ON m.category_id = c.id
                WHERE c.vendor_id = :vendor_id
            """), {'vendor_id': vendor_id}).fetchall()]
            
            if menu_ids:
                # Delete images for these menus
                db.session.execute(text("""
                    DELETE FROM extra_service_menu_images
                    WHERE menu_id = ANY(:menu_ids)
                """), {'menu_ids': menu_ids})
                
                # Then delete the menus
                db.session.execute(text("""
                    DELETE FROM extra_service_menus
                    WHERE id = ANY(:menu_ids)
                """), {'menu_ids': menu_ids})

            # Step 13: Delete User Passes first
            current_app.logger.debug("Deleting User Passes linked to vendor's cafe passes")
            db.session.execute(text("""
                DELETE FROM user_passes
                WHERE cafe_pass_id IN (
                    SELECT id FROM cafe_passes WHERE vendor_id = :vendor_id
                )
            """), {'vendor_id': vendor_id})

            # Step 13: Delete Cafe Passes
            current_app.logger.debug("Deleting Cafe Passes")
            db.session.execute(text("""
                DELETE FROM cafe_passes
                WHERE vendor_id = :vendor_id
            """), {'vendor_id': vendor_id})

            # Step 14: Delete Vendor record itself
            current_app.logger.debug("Deleting Vendor record")
            db.session.delete(vendor)

            # Step 14: Drop vendor-specific dynamic tables
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
    
        # Safe email retrieval with fallback
        email = None
    
        if vendor.account and vendor.account.email:
            # First try: get email from vendor account
            email = vendor.account.email
            current_app.logger.debug(f"Using vendor account email: {email}")
        else:
            # Fallback: get email from contact info
            contact_info = ContactInfo.query.filter_by(
               parent_id=vendor.id, 
               parent_type="vendor"
             ).first()
        
            if contact_info and contact_info.email:
              email = contact_info.email
              current_app.logger.debug(f"Using contact info email: {email}")
            else:
               current_app.logger.error(f"No email found for vendor {vendor.id}")
               raise ValueError(f"No email found for vendor {vendor.id}")
    
        current_app.logger.debug(f"Processing credentials for vendor {vendor.id} with email: {email}")

        # Step 1: Check if PasswordManager already exists for this email
        existing_password_manager = (
           db.session.query(PasswordManager)
           .join(Vendor, Vendor.id == PasswordManager.parent_id)
            .join(ContactInfo, and_(
               ContactInfo.parent_id == Vendor.id,
               ContactInfo.parent_type == 'vendor'
           ))
           .filter(ContactInfo.email == email)
           .filter(PasswordManager.parent_type == 'vendor') 
           .first()
        )

        if existing_password_manager:
            # Already has credentials — link this vendor to same account
            password_manager = existing_password_manager
            username = email
            password = "****** (existing account - check previous email)"
            current_app.logger.info(f"Linked vendor {vendor.id} to existing credentials.")
        else:
            # ✅ UPDATED: Check if password was provided during onboarding
            if hasattr(vendor, '_temp_password') and vendor._temp_password:
                username = email
                password = vendor._temp_password
                current_app.logger.info(f"Using provided password for vendor {vendor.id}")
            else:
                # Generate new credentials
                username, password = generate_credentials()
                current_app.logger.info(f"Generated new password for vendor {vendor.id}")
            
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
        
        # ✅ UPDATED: Get the PIN and pass to email
        vendor_pin = VendorPin.query.filter_by(vendor_id=vendor.id).first()
        pin_code = vendor_pin.pin_code if vendor_pin else "N/A"
        
        VendorService.send_welcome_email(vendor, username, password, email, pin_code)
        current_app.logger.info(f"Completed credentials generation for vendor {vendor.id}")

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
        Retrieve all vendors with their statuses, timing info, amenities, and images for the salesperson dashboard.
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

            amenities_map = {}
            for amenity in amenities:
                amenities_map.setdefault(amenity.vendor_id, []).append({
                    "name": amenity.name,
                    "available": amenity.available
                })

            # Step 3: Fetch all images for those vendors
            images = db.session.query(
                Image.vendor_id,
                Image.image_id,
                Image.path,
                Image.public_id,
                Image.url
            ).filter(Image.vendor_id.in_(vendor_ids)).all()

            images_map = {}
            for img in images:
                images_map.setdefault(img.vendor_id, []).append({
                    "image_id": img.image_id,
                    "url": img.url,
                    "public_id":img.public_id
                })
                
            payment_methods_map = VendorService.get_payment_methods_for_vendors(vendor_ids)

            # Step 4: Combine all datasets
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
                    "amenities": amenities_map.get(result.vendor_id, []),
                    "images": images_map.get(result.vendor_id, []),
                    "payment_methods": payment_methods_map.get(result.vendor_id, {
                        "Pay at Cafe": False,
                        "Hash": False
                    })
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
        
    @staticmethod
    def get_payment_methods_for_vendors(vendor_ids):
        """Payment Method"""
        try:
            payment_methods_map = {}
        
            for vendor_id in vendor_ids:
                payment_status = {}
            
            # Method 1: Check Pay at Cafe using subquery
                pay_cafe_exists = db.session.query(
                    db.session.query(PaymentVendorMap).join(PaymentMethod).filter(
                      PaymentVendorMap.vendor_id == vendor_id,
                      PaymentMethod.method_name == 'Pay at Cafe'
                ).exists()
            ).scalar()
                payment_status['Pay at Cafe'] = pay_cafe_exists
            
            # Method 2: Check Hash using subquery  
                hash_exists = db.session.query(
                    db.session.query(PaymentVendorMap).join(PaymentMethod).filter(
                       PaymentVendorMap.vendor_id == vendor_id,
                       PaymentMethod.method_name == 'Hash'
                ).exists()
            ).scalar()
                payment_status['Hash'] = hash_exists
            
                payment_methods_map[vendor_id] = payment_status
        
            current_app.logger.info(f"Payment methods result: {payment_methods_map}")
            return payment_methods_map

        except Exception as e:
          current_app.logger.error(f"Error in get_payment_methods_for_vendors: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return {vendor_id: {"Pay at Cafe": False, "Hash": False} for vendor_id in vendor_ids}
    
    
    @staticmethod
    def send_welcome_email(vendor, username, password, email, pin_code):
        """✅ UPDATED: Send welcome email with vendor credentials and PIN."""
        
        try:
            # Create email message
            msg = Message(
                subject='Welcome to Hash for Gamers - Your Vendor Credentials',
                sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@hashforgamers.com'),
                recipients=[email]
            )

            # Email HTML template
            html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                .credentials-box {{ background: #ffffff; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
                .credential-item {{ margin: 10px 0; padding: 10px; background: #e9ecef; border-radius: 5px; }}
                .credential-label {{ font-weight: bold; color: #495057; }}
                .credential-value {{ color: #007bff; font-family: monospace; font-size: 16px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #6c757d; font-size: 12px; }}
                .status-badge {{ display: inline-block; padding: 5px 15px; background: #ffc107; color: #212529; border-radius: 20px; font-size: 12px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎮 Welcome to Hash for Gamers!</h1>
                    <p>Your gaming cafe has been successfully onboarded</p>
                </div>
                
                <div class="content">
                    <h2>Hello {vendor.owner_name}!</h2>
                    <p>Congratulations! <strong>{vendor.cafe_name}</strong> has been successfully registered with Hash for Gamers.</p>
                    
                    <div class="credentials-box">
                        <h3>Your Vendor Credentials:</h3>
                        
                        <div class="credential-item">
                            <span class="credential-label">Username:</span><br>
                            <span class="credential-value">{username}</span>
                        </div>
                        
                        <div class="credential-item">
                            <span class="credential-label">Password:</span><br>
                            <span class="credential-value">{password}</span>
                        </div>
                        
                        <div class="credential-item">
                            <span class="credential-label">Vendor PIN:</span><br>
                            <span class="credential-value">{pin_code}</span>
                        </div>
                        
                        <div style="margin-top: 15px;">
                            <span class="credential-label">Account Status:</span><br>
                            <span class="status-badge">Pending Verification</span>
                        </div>
                    </div>
                    
                    <h3>Next Steps:</h3>
                    <ul>
                        <li>🔍 Our team will verify your submitted documents</li>
                        <li>📧 You'll receive a confirmation email once verified</li>
                        <li>🚀 After verification, you can start using our platform</li>
                        <li>💡 Keep your credentials safe and secure</li>
                    </ul>
                    
                    <h3>Important Information:</h3>
                    <ul>
                        <li><strong>Vendor ID:</strong> {vendor.id}</li>
                        <li><strong>Registration Email:</strong> {email}</li>
                        <li><strong>Cafe Name:</strong> {vendor.cafe_name}</li>
                        <li><strong>Owner:</strong> {vendor.owner_name}</li>
                    </ul>
                    
                    <p><strong>⚠️ Security Notice:</strong> Please keep your login credentials secure and do not share them with unauthorized personnel.</p>
                </div>
                
                <div class="footer">
                    <p>This is an automated message from Hash for Gamers</p>
                    <p>If you have any questions, please contact our support team</p>
                    <p>© 2025 Hash for Gamers. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

            msg.html = html_body

            # Send the email
            mail.send(msg)
            current_app.logger.info(f"Welcome email sent successfully to {email} for vendor {vendor.id}")

        except Exception as e:
          current_app.logger.error(f"Failed to send welcome email to {email} for vendor {vendor.id}: {str(e)}")
        # Don't raise the exception as email failure shouldn't stop onboarding
          pass
      
    @staticmethod
    def send_deboard_notification(vendor_id):
        """Fetch vendor info and send a deboard warning email."""
        current_app.logger.info(f"Sending deboard notification for vendor ID: {vendor_id}")

        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            raise ValueError(f"No vendor found with ID {vendor_id}")

        # Resolve email — account first, then contact_info fallback
        email = None
        if vendor.account and vendor.account.email:
            email = vendor.account.email
        else:
            contact = ContactInfo.query.filter_by(
                parent_id=vendor_id, parent_type="vendor"
            ).first()
            if contact and contact.email:
                email = contact.email

        if not email:
            raise ValueError(f"No email address found for vendor {vendor_id}")

        owner_name = vendor.owner_name or "Vendor"
        cafe_name  = vendor.cafe_name  or f"Vendor #{vendor_id}"

        html_body = VendorService._build_deboard_email_html(owner_name, cafe_name, vendor_id)

        msg = Message(
            subject=f"Important Notice: Your Cafe Account — {cafe_name}",
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@hashforgamers.com'),
            recipients=[email]
        )
        msg.html = html_body

        mail.send(msg)
        current_app.logger.info(f"Deboard notification sent to {email} for vendor {vendor_id}")

        return {
            'success': True,
            'message': f'Notification sent to {email}',
            'vendor_id': vendor_id,
            'cafe_name': cafe_name
        }

    @staticmethod
    def _build_deboard_email_html(owner_name: str, cafe_name: str, vendor_id: int) -> str:
        """Build the dark-themed deboard warning HTML email."""

        deletion_items = [
            "All bookings, transactions &amp; payment records",
            "Slots, available games &amp; console associations",
            "Cafe passes &amp; user passes",
            "Amenities, opening days &amp; timing configuration",
            "Uploaded documents &amp; business registration",
            "All vendor-specific data tables",
        ]

        deletion_rows = "".join([
            f"""
                <tr>
                  <td style="padding:6px 0;border-bottom:1px solid #1a1a1a;">
                    <span style="color:#ff4444;margin-right:10px;">&#10005;</span>
                    <span style="color:#aaaaaa;font-size:13px;">{item}</span>
                  </td>
                </tr>"""
            for item in deletion_items
        ])

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Account Notice - Hash for Gamers</title>
</head>
<body style="margin:0;padding:0;background-color:#080808;font-family:'Segoe UI',Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#080808;padding:40px 0;">
    <tr>
      <td align="center">

        <table width="600" cellpadding="0" cellspacing="0" border="0"
               style="background-color:#0f0f0f;border-radius:12px;
                      border:1px solid #1f1f1f;overflow:hidden;
                      box-shadow:0 4px 40px rgba(0,0,0,0.8);">

          <!-- HEADER -->
          <tr>
            <td style="background:linear-gradient(135deg,#0f0f0f 0%,#1a0000 50%,#0f0f0f 100%);
                       border-bottom:1px solid #2a0000;padding:36px 40px;text-align:center;">

              <div style="display:inline-block;background:#1a0000;border:1px solid #ff3333;
                          border-radius:8px;padding:8px 20px;margin-bottom:20px;">
                <span style="color:#ff3333;font-size:13px;font-weight:700;
                             letter-spacing:3px;text-transform:uppercase;">
                  Hash for Gamers
                </span>
              </div>

              <div style="margin:0 auto 16px;width:64px;height:64px;
                          background:#1a0000;border:2px solid #ff3333;
                          border-radius:50%;line-height:64px;text-align:center;
                          font-size:28px;">
                &#9888;
              </div>

              <h1 style="color:#ffffff;font-size:22px;font-weight:700;
                         margin:0;letter-spacing:0.5px;">
                Important Account Notice
              </h1>
              <p style="color:#888888;font-size:13px;margin:8px 0 0;letter-spacing:0.5px;">
                Action Required &mdash; Please Read Carefully
              </p>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:40px 40px 20px;">

              <p style="color:#cccccc;font-size:15px;line-height:1.6;margin:0 0 24px;">
                Dear <strong style="color:#ffffff;">{owner_name}</strong>,
              </p>

              <p style="color:#cccccc;font-size:15px;line-height:1.6;margin:0 0 32px;">
                We are reaching out regarding your gaming cafe registered with us &mdash;
                <strong style="color:#ffffff;">{cafe_name}</strong>
                <span style="color:#555555;font-size:12px;">(ID: #{vendor_id})</span>.
              </p>

              <!-- Alert Box -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:#130000;border:1px solid #ff3333;
                            border-left:4px solid #ff3333;border-radius:8px;
                            margin-bottom:32px;">
                <tr>
                  <td style="padding:20px 24px;">
                    <p style="color:#ff6666;font-size:14px;font-weight:700;
                               margin:0 0 8px;text-transform:uppercase;letter-spacing:1px;">
                      Deboarding Notice
                    </p>
                    <p style="color:#cccccc;font-size:14px;line-height:1.7;margin:0;">
                      Your cafe account has been flagged for
                      <strong style="color:#ffffff;">removal from the Hash for Gamers platform</strong>.
                      All associated data &mdash; including bookings, slots, transactions,
                      and configurations &mdash; will be
                      <strong style="color:#ff6666;">permanently deleted</strong>.
                    </p>
                  </td>
                </tr>
              </table>

              <!-- What will be removed -->
              <p style="color:#888888;font-size:12px;font-weight:700;letter-spacing:2px;
                         text-transform:uppercase;margin:0 0 12px;">
                What will be removed
              </p>

              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-bottom:32px;">
                {deletion_rows}
              </table>

              <p style="color:#cccccc;font-size:15px;line-height:1.6;margin:0 0 16px;">
                If you believe this is an error or wish to dispute this action,
                please contact our support team
                <strong style="color:#ffffff;">immediately</strong>.
              </p>

              <!-- Support Button -->
              <table cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;">
                <tr>
                  <td style="background-color:#1a0000;border:1px solid #ff3333;
                              border-radius:8px;padding:14px 32px;text-align:center;">
                    <a href="mailto:support@hashforgamers.com"
                       style="color:#ff6666;font-size:14px;font-weight:700;
                              text-decoration:none;letter-spacing:0.5px;">
                      Contact Support
                    </a>
                  </td>
                </tr>
              </table>

              <div style="border-top:1px solid #1a1a1a;margin:32px 0;"></div>

              <!-- Info note -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="background-color:#111111;border-radius:8px;
                            border:1px solid #1f1f1f;margin-bottom:8px;">
                <tr>
                  <td style="padding:16px 20px;">
                    <p style="color:#555555;font-size:12px;line-height:1.6;margin:0;">
                      This is an automated notice sent by the Hash for Gamers admin platform.
                      If you have already been in contact with our team, please disregard this email.
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color:#0a0a0a;border-top:1px solid #1a1a1a;
                       padding:24px 40px;text-align:center;">
              <p style="color:#ff3333;font-size:12px;font-weight:700;
                         letter-spacing:2px;text-transform:uppercase;margin:0 0 8px;">
                Hash for Gamers
              </p>
              <p style="color:#333333;font-size:11px;margin:0;">
                &copy; 2026 Hash for Gamers. All rights reserved.
              </p>
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>

</body>
</html>"""
