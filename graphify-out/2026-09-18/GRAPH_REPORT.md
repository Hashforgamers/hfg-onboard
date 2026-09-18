# Graph Report - hfg-onboard  (2026-09-18)

## Corpus Check
- 65 files · ~38,348 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 553 nodes · 1388 edges · 32 communities (28 shown, 4 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b6854bce`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- vendor_games.py
- vendor.py
- SuperAdminService
- order_controller.py
- super_admin_controller.py
- route
- onboard_vendor
- controllers.py
- extensions.py
- cron_extend_slots_for_all_active_cafes
- OTPService
- upload_vendor_missing_document
- VendorService
- .search_gaming_cafes
- upload_photos
- console_catalog
- test_self_onboarding_flow.py
- .save_image_to_db
- build_hfg_email_html
- MemoryRedis
- PaymentMethod
- services.py
- AGENTS.md
- ConsolePricingOffer
- Booking
- get_unverified_documents
- .onboard_vendor
- verify_document
- get_vendor_dashboard
- password_manager

## God Nodes (most connected - your core abstractions)
1. `SuperAdminService` - 79 edges
2. `VendorService` - 69 edges
3. `Vendor` - 31 edges
4. `require_super_admin()` - 30 edges
5. `build_hfg_email_html()` - 22 edges
6. `GameService` - 17 edges
7. `onboard_vendor()` - 16 edges
8. `CloudinaryGameImageService` - 15 edges
9. `VendorStatus` - 14 edges
10. `PasswordManager` - 13 edges

## Surprising Connections (you probably didn't know these)
- `VendorService` --uses--> `AdditionalDetails`  [INFERRED]
  services/services.py → models/additionalDetails.py
- `VendorService` --uses--> `Amenity`  [INFERRED]
  services/services.py → models/amenity.py
- `VendorService` --uses--> `AvailableGame`  [INFERRED]
  services/services.py → models/availableGame.py
- `VendorService` --uses--> `Booking`  [INFERRED]
  services/services.py → models/booking.py
- `VendorService` --uses--> `BusinessRegistration`  [INFERRED]
  services/services.py → models/businessRegistration.py

## Import Cycles
- None detected.

## Communities (32 total, 4 thin omitted)

### Community 0 - "vendor_games.py"
Cohesion: 0.07
Nodes (32): add_cover_image(), add_supported_game(), create_game(), create_games_batch(), delete_supported_game(), get_all_games(), health_check(), list_game_discovery_platforms() (+24 more)

### Community 1 - "vendor.py"
Cohesion: 0.17
Nodes (10): datetime, ContactInfo, DocumentSubmitted, PhysicalAddress, Timing, Transaction, Vendor, VendorAccount (+2 more)

### Community 2 - "SuperAdminService"
Cohesion: 0.07
Nodes (3): Any, date, SuperAdminService

### Community 3 - "order_controller.py"
Cohesion: 0.10
Nodes (30): Config, create_app(), _is_insecure_secret(), _validate_production_config(), add_product(), create_collaborator(), delete_collaborator(), delete_product() (+22 more)

### Community 4 - "super_admin_controller.py"
Cohesion: 0.13
Nodes (37): change_subscription(), claim_early_onboard_promotion(), create_vendor_staff(), deboard_vendor_admin(), delete_subscription_model(), delete_vendor_staff(), get_daily_settlement_summary(), get_vendor() (+29 more)

### Community 5 - "route"
Cohesion: 0.07
Nodes (28): check_verification(), get_all_gaming_cafe(), get_vendor_dashboard_data(), get_vendor_photos(), health_check(), insert_to_queue(), kiosk_next_slot_check_proxy(), kiosk_next_slot_confirm_proxy() (+20 more)

### Community 6 - "onboard_vendor"
Cohesion: 0.15
Nodes (21): _apply_branch_defaults(), _build_branch_defaults_from_vendor(), _consume_self_onboard_verification_token(), _get_branch_defaults_for_email(), get_branch_onboard_defaults(), _is_missing_payload_value(), _normalize_cafe_name(), _normalize_email() (+13 more)

### Community 7 - "controllers.py"
Cohesion: 0.17
Nodes (19): allowed_file(), _apply_slot_rows_for_day(), _emit_unlock(), _generate_blocks(), _is_valid_email(), normalize_day_key(), _normalize_phone(), parse_time_flexible() (+11 more)

### Community 8 - "extensions.py"
Cohesion: 0.13
Nodes (9): check_redis_health(), create_redis_pool(), Create a Redis connection pool to reuse connections This prevents repeated SSL…, Check Redis connection health, AvailableGame, Serialize VendorGame — price is always dynamically computed, Dynamically compute price from parent AvailableGame. - If an active…, Returns full pricing context: base price, offer price, offer details. Useful… (+1 more)

### Community 9 - "cron_extend_slots_for_all_active_cafes"
Cohesion: 0.14
Nodes (14): cron_extend_slots_for_all_active_cafes(), cron_extend_slots_for_vendor(), _ensure_vendor_slot_table_exists(), extend_slot_window(), _fetch_active_vendor_ids_for_slots(), _is_valid_cron_request(), Extend slot inventory horizon without regenerating existing dates. Payload: {…, Optional shared-secret gate for cron endpoints. If CRON_JOB_API_KEY is unset,… (+6 more)

### Community 10 - "OTPService"
Cohesion: 0.14
Nodes (9): OTPService, Verify the provided OTP - FAST, Send email asynchronously in background thread, Check if vendor is already verified - INSTANT Just checks Redis - no database…, Clear verification status, Clear all verification status for a vendor (for logout), Generate a random numeric OTP, Send OTP to vendor's email - OPTIMIZED FOR SPEED Returns immediately while… (+1 more)

### Community 11 - "upload_vendor_missing_document"
Cohesion: 0.15
Nodes (12): delete_vendor_image(), delete_vendor_image_by_url(), Upload a missing (or replace existing) required onboarding document by…, Replace an existing vendor document file. Note: Replaced doc status becomes…, Deletes a vendor image from both Cloudinary and the database by image ID., Deletes a vendor image by URL from both Cloudinary and the database., Upload vendor documents to Cloudinary and return URLs, replace_vendor_document() (+4 more)

### Community 12 - "VendorService"
Cohesion: 0.18
Nodes (5): deboard_vendor(), Document, Upload a file to Google Drive and return the file link., Update specified documents' status to 'verified' and set the vendor's status to…, VendorService

### Community 13 - ".search_gaming_cafes"
Cohesion: 0.22
Nodes (3): Retrieve all vendors with their statuses, timing info, amenities, images, and…, Lightweight app discovery search for cafes offering a game. Designed for high…, OPTIMIZED: Fetch payment methods for ALL vendors in a single query. Previously…

### Community 14 - "upload_photos"
Cohesion: 0.40
Nodes (4): API endpoint to upload photos to Google Drive., upload_photos(), Initialize and return the Google Drive service., Initialize and return the Google Drive service.

### Community 15 - "console_catalog"
Cohesion: 0.60
Nodes (5): console_catalog, games, game_console_catalog, game_discovery_events, game_popularity_rankings

### Community 16 - "test_self_onboarding_flow.py"
Cohesion: 0.18
Nodes (5): declared_attr, PasswordManager, Slot, VendorDaySlotConfig, Onboarding integration tests: real Flask/ORM, isolated DB, mocked external IO.

### Community 17 - ".save_image_to_db"
Cohesion: 0.33
Nodes (3): Save image metadata to the database. Args: vendor_id (int): ID of the vendor…, Upload a single photo to Google Drive and return the file link., Upload multiple photos to Google Drive and return their file links.

### Community 18 - "build_hfg_email_html"
Cohesion: 0.10
Nodes (15): build_hfg_email_html(), _extract_body(), Send invoice notification email with table format, Send standardized onboarding email with vendor credentials., Build welcome email content fragment (wrapped by shared HFG template)., Fetch vendor info and send a deboard warning email., Build deboard warning content fragment (wrapped by shared HFG template)., Generate account credentials and notify vendor with login details. (+7 more)

### Community 19 - "MemoryRedis"
Cohesion: 0.19
Nodes (9): fixture, app(), MemoryRedis, payload(), submit(), test_active_cafe_credentials_and_schedule(), test_document_failure_rolls_back_and_can_retry(), test_email_failure_preserves_account_and_reports_failure() (+1 more)

### Community 21 - "services.py"
Cohesion: 0.11
Nodes (9): AdditionalDetails, Amenity, BusinessRegistration, Console, MaintenanceStatus, PaymentVendorMap, PriceAndCost, Image (+1 more)

### Community 23 - "ConsolePricingOffer"
Cohesion: 0.28
Nodes (5): ConsolePricingOffer, Time-based promotional pricing for console types (AvailableGames) Allows…, Check if this offer is active RIGHT NOW using IST. Returns True if current IST…, Calculate discount percentage, Convert to dictionary for API responses

### Community 25 - "get_unverified_documents"
Cohesion: 0.50
Nodes (3): get_unverified_documents(), API endpoint to get all unverified document file paths for a given vendor., Fetch all unverified documents for the specified vendor.

### Community 26 - ".onboard_vendor"
Cohesion: 0.12
Nodes (7): HardwareSpecification, OpeningDay, Creates a table for tracking console availability for a vendor., Creates a table for tracking vendor dashboard details., Creates a vendor-specific promo detail table., Safely parse date string, handling None and invalid values, generate_unique_vendor_pin()

### Community 27 - "verify_document"
Cohesion: 0.50
Nodes (3): API endpoint to mark a document as verified and update vendor status if…, verify_document(), Mark a document as verified and set the vendor's status to active if all…

### Community 28 - "get_vendor_dashboard"
Cohesion: 0.50
Nodes (3): get_vendor_dashboard(), API to retrieve all vendors with their statuses and relevant information for…, Retrieve all vendors with their statuses, timing info, and relevant information…

## Knowledge Gaps
- **2 isolated node(s):** `Invoice`, `graphify`
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VendorService` connect `VendorService` to `vendor_games.py`, `vendor.py`, `SuperAdminService`, `super_admin_controller.py`, `controllers.py`, `extensions.py`, `cron_extend_slots_for_all_active_cafes`, `.search_gaming_cafes`, `upload_photos`, `test_self_onboarding_flow.py`, `.save_image_to_db`, `build_hfg_email_html`, `MemoryRedis`, `PaymentMethod`, `services.py`, `Booking`, `get_unverified_documents`, `.onboard_vendor`, `verify_document`, `get_vendor_dashboard`?**
  _High betweenness centrality (0.248) - this node is a cross-community bridge._
- **Why does `SuperAdminService` connect `SuperAdminService` to `vendor.py`, `super_admin_controller.py`, `VendorService`, `test_self_onboarding_flow.py`, `services.py`?**
  _High betweenness centrality (0.195) - this node is a cross-community bridge._
- **Why does `Vendor` connect `vendor.py` to `vendor_games.py`, `SuperAdminService`, `order_controller.py`, `controllers.py`, `extensions.py`, `OTPService`, `VendorService`, `test_self_onboarding_flow.py`, `MemoryRedis`, `services.py`, `.onboard_vendor`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SuperAdminService` (e.g. with `VendorService` and `ContactInfo`) actually correct?**
  _`SuperAdminService` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `VendorService` (e.g. with `AdditionalDetails` and `Amenity`) actually correct?**
  _`VendorService` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `Vendor` (e.g. with `Amenity` and `AvailableGame`) actually correct?**
  _`Vendor` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Invoice`, `graphify` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._