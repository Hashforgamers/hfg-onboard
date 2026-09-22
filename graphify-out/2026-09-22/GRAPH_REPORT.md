# Graph Report - hfg-onboard  (2026-09-18)

## Corpus Check
- 65 files · ~38,773 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 561 nodes · 1399 edges · 36 communities (23 shown, 13 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 74 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `595cf12c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- vendor_games.py
- services.py
- SuperAdminService
- extensions.py
- super_admin_controller.py
- route
- onboard_vendor
- controllers.py
- AvailableGame
- cron_extend_slots_for_all_active_cafes
- OTPService
- Document
- VendorService
- .search_gaming_cafes
- upload_photos
- console_catalog
- send_self_onboard_email_otp
- Image
- .send_welcome_email
- test_self_onboarding_flow.py
- PaymentMethod
- PaymentVendorMap
- AGENTS.md
- _EmailText
- Booking
- .get_unverified_documents
- .create_vendor_console_availability_table
- .verify_document
- .get_all_vendors_with_status
- password_manager
- .send_deboard_notification
- .create_vendor_promo_table
- .safe_strptime
- .verify_documents_and_update_vendor

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

## Communities (36 total, 13 thin omitted)

### Community 0 - "vendor_games.py"
Cohesion: 0.07
Nodes (32): add_cover_image(), add_supported_game(), create_game(), create_games_batch(), delete_supported_game(), get_all_games(), health_check(), list_game_discovery_platforms() (+24 more)

### Community 1 - "services.py"
Cohesion: 0.07
Nodes (31): declared_attr, AdditionalDetails, Amenity, BusinessRegistration, Console, ContactInfo, DocumentSubmitted, HardwareSpecification (+23 more)

### Community 2 - "SuperAdminService"
Cohesion: 0.08
Nodes (3): Any, date, SuperAdminService

### Community 3 - "extensions.py"
Cohesion: 0.08
Nodes (36): Config, create_app(), _is_insecure_secret(), _validate_production_config(), add_product(), create_collaborator(), delete_collaborator(), delete_product() (+28 more)

### Community 4 - "super_admin_controller.py"
Cohesion: 0.14
Nodes (36): change_subscription(), claim_early_onboard_promotion(), create_vendor_staff(), deboard_vendor_admin(), delete_subscription_model(), delete_vendor_staff(), get_daily_settlement_summary(), get_vendor() (+28 more)

### Community 5 - "route"
Cohesion: 0.06
Nodes (33): check_verification(), deboard_vendor(), get_all_gaming_cafe(), get_unverified_documents(), get_vendor_dashboard(), get_vendor_dashboard_data(), get_vendor_photos(), insert_to_queue() (+25 more)

### Community 6 - "onboard_vendor"
Cohesion: 0.17
Nodes (19): _apply_branch_defaults(), _build_branch_defaults_from_vendor(), _consume_self_onboard_verification_token(), _get_branch_defaults_for_email(), get_branch_onboard_defaults(), _is_missing_payload_value(), _normalize_cafe_name(), _normalize_email() (+11 more)

### Community 7 - "controllers.py"
Cohesion: 0.17
Nodes (14): allowed_file(), _apply_slot_rows_for_day(), _emit_unlock(), _generate_blocks(), health_check(), normalize_day_key(), parse_time_flexible(), Emit unlock signal to internal WebSocket service (+6 more)

### Community 8 - "AvailableGame"
Cohesion: 0.12
Nodes (10): AvailableGame, ConsolePricingOffer, Time-based promotional pricing for console types (AvailableGames) Allows…, Check if this offer is active RIGHT NOW using IST. Returns True if current IST…, Calculate discount percentage, Convert to dictionary for API responses, Serialize VendorGame — price is always dynamically computed, Dynamically compute price from parent AvailableGame. - If an active… (+2 more)

### Community 9 - "cron_extend_slots_for_all_active_cafes"
Cohesion: 0.14
Nodes (14): cron_extend_slots_for_all_active_cafes(), cron_extend_slots_for_vendor(), _ensure_vendor_slot_table_exists(), extend_slot_window(), _fetch_active_vendor_ids_for_slots(), _is_valid_cron_request(), Extend slot inventory horizon without regenerating existing dates. Payload: {…, Optional shared-secret gate for cron endpoints. If CRON_JOB_API_KEY is unset,… (+6 more)

### Community 10 - "OTPService"
Cohesion: 0.14
Nodes (9): OTPService, Verify the provided OTP - FAST, Check if vendor is already verified - INSTANT Just checks Redis - no database…, Send email asynchronously in background thread, Clear verification status, Clear all verification status for a vendor (for logout), Generate a random numeric OTP, Send OTP to vendor's email - OPTIMIZED FOR SPEED Returns immediately while… (+1 more)

### Community 11 - "Document"
Cohesion: 0.12
Nodes (15): delete_vendor_image(), delete_vendor_image_by_url(), Upload a missing (or replace existing) required onboarding document by…, Replace an existing vendor document file. Note: Replaced doc status becomes…, Deletes a vendor image from both Cloudinary and the database by image ID., Deletes a vendor image by URL from both Cloudinary and the database., Upload vendor documents to Cloudinary and return URLs, Save uploaded document metadata once; avoid duplicate inserts and loop commits. (+7 more)

### Community 12 - "VendorService"
Cohesion: 0.27
Nodes (3): Creates a table for tracking vendor dashboard details., Upload a file to Google Drive and return the file link., VendorService

### Community 13 - ".search_gaming_cafes"
Cohesion: 0.22
Nodes (3): Retrieve all vendors with their statuses, timing info, amenities, images, and…, Lightweight app discovery search for cafes offering a game. Designed for high…, OPTIMIZED: Fetch payment methods for ALL vendors in a single query. Previously…

### Community 14 - "upload_photos"
Cohesion: 0.29
Nodes (5): API endpoint to upload photos to Google Drive., upload_photos(), Initialize and return the Google Drive service., Upload multiple photos to Google Drive and return their file links., Initialize and return the Google Drive service.

### Community 15 - "console_catalog"
Cohesion: 0.60
Nodes (5): console_catalog, games, game_console_catalog, game_discovery_events, game_popularity_rankings

### Community 16 - "send_self_onboard_email_otp"
Cohesion: 0.36
Nodes (8): _is_valid_email(), _normalize_phone(), _self_onboard_duplicate_reason(), _self_onboard_otp_cooldown_key(), _self_onboard_otp_key(), _self_onboard_verify_key(), send_self_onboard_email_otp(), verify_self_onboard_email_otp()

### Community 17 - "Image"
Cohesion: 0.40
Nodes (3): Image, Save image metadata to the database. Args: vendor_id (int): ID of the vendor…, Upload a single photo to Google Drive and return the file link.

### Community 18 - ".send_welcome_email"
Cohesion: 0.33
Nodes (3): Send standardized onboarding email with vendor credentials., Build welcome email content fragment (wrapped by shared HFG template)., test_welcome_html_escapes_owner_data()

### Community 19 - "test_self_onboarding_flow.py"
Cohesion: 0.15
Nodes (12): fixture, Slot, VendorDaySlotConfig, app(), MemoryRedis, payload(), Onboarding integration tests: real Flask/ORM, isolated DB, mocked external IO., submit() (+4 more)

### Community 23 - "_EmailText"
Cohesion: 0.29
Nodes (3): HTMLParser, _EmailText, Generate a useful plain-text alternative, retaining links and table values.

## Knowledge Gaps
- **2 isolated node(s):** `Invoice`, `graphify`
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VendorService` connect `VendorService` to `vendor_games.py`, `services.py`, `SuperAdminService`, `super_admin_controller.py`, `controllers.py`, `AvailableGame`, `cron_extend_slots_for_all_active_cafes`, `Document`, `.search_gaming_cafes`, `upload_photos`, `Image`, `.send_welcome_email`, `test_self_onboarding_flow.py`, `PaymentMethod`, `PaymentVendorMap`, `Booking`, `.get_unverified_documents`, `.create_vendor_console_availability_table`, `.verify_document`, `.get_all_vendors_with_status`, `.send_deboard_notification`, `.create_vendor_promo_table`, `.safe_strptime`, `.verify_documents_and_update_vendor`?**
  _High betweenness centrality (0.243) - this node is a cross-community bridge._
- **Why does `SuperAdminService` connect `SuperAdminService` to `services.py`, `Document`, `super_admin_controller.py`, `VendorService`?**
  _High betweenness centrality (0.192) - this node is a cross-community bridge._
- **Why does `Vendor` connect `services.py` to `vendor_games.py`, `SuperAdminService`, `extensions.py`, `controllers.py`, `AvailableGame`, `OTPService`, `VendorService`, `test_self_onboarding_flow.py`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SuperAdminService` (e.g. with `VendorService` and `ContactInfo`) actually correct?**
  _`SuperAdminService` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `VendorService` (e.g. with `AdditionalDetails` and `Amenity`) actually correct?**
  _`VendorService` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `Vendor` (e.g. with `Amenity` and `AvailableGame`) actually correct?**
  _`Vendor` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Invoice`, `graphify` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._