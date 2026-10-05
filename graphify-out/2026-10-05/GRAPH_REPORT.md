# Graph Report - hfg-onboard  (2026-10-05)

## Corpus Check
- 78 files · ~42,735 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 636 nodes · 1520 edges · 42 communities (26 shown, 16 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 83 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `dfa21706`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- vendor_games.py
- controllers.py
- SuperAdminService
- extensions.py
- super_admin_controller.py
- route
- onboard_vendor
- test_self_onboarding_flow.py
- ConsolePricingOffer
- Image
- OTPService
- replace_vendor_document
- VendorService
- .search_gaming_cafes
- upload_photos
- console_catalog
- services.py
- .send_deboard_notification
- CatalogProxyTests
- .send_welcome_email
- .extend_vendor_slot_window
- Document
- AGENTS.md
- kiosk-releases.md
- .create_vendor_console_availability_table
- DocumentReviewTests
- .verify_document
- .get_all_vendors_with_status
- password_manager
- test_operating_hours.py
- cafe_requests
- test_kiosk_releases.py
- operating-hours.md
- _EmailText
- PaymentMethod
- PaymentVendorMap
- .get_unverified_documents
- .verify_documents_and_update_vendor
- 20261005_kiosk_releases.sql

## God Nodes (most connected - your core abstractions)
1. `SuperAdminService` - 80 edges
2. `VendorService` - 69 edges
3. `require_super_admin()` - 34 edges
4. `Vendor` - 32 edges
5. `build_hfg_email_html()` - 22 edges
6. `GameService` - 17 edges
7. `onboard_vendor()` - 16 edges
8. `CloudinaryGameImageService` - 15 edges
9. `PasswordManager` - 13 edges
10. `VendorStatus` - 13 edges

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

## Communities (42 total, 16 thin omitted)

### Community 0 - "vendor_games.py"
Cohesion: 0.07
Nodes (32): add_cover_image(), add_supported_game(), create_game(), create_games_batch(), delete_supported_game(), get_all_games(), health_check(), list_game_discovery_platforms() (+24 more)

### Community 1 - "controllers.py"
Cohesion: 0.13
Nodes (14): allowed_file(), _emit_unlock(), _normalize_cafe_name(), Emit unlock signal to internal WebSocket service, # IMPORTANT: Fetch real documents from your Document model, Check if the file has an allowed extension., Validate the JSON data for required fields., Save uploaded document metadata once; avoid duplicate inserts and loop commits. (+6 more)

### Community 2 - "SuperAdminService"
Cohesion: 0.07
Nodes (3): Any, date, SuperAdminService

### Community 3 - "extensions.py"
Cohesion: 0.06
Nodes (41): Config, create_app(), _is_insecure_secret(), _validate_production_config(), add_product(), create_collaborator(), delete_collaborator(), delete_product() (+33 more)

### Community 4 - "super_admin_controller.py"
Cohesion: 0.11
Nodes (43): activate_kiosk_release(), change_subscription(), claim_early_onboard_promotion(), create_vendor_staff(), deboard_vendor_admin(), delete_subscription_model(), delete_vendor_staff(), get_daily_settlement_summary() (+35 more)

### Community 5 - "route"
Cohesion: 0.06
Nodes (35): check_verification(), deboard_vendor(), get_all_gaming_cafe(), get_unverified_documents(), get_vendor_dashboard(), get_vendor_dashboard_data(), get_vendor_photos(), health_check() (+27 more)

### Community 6 - "onboard_vendor"
Cohesion: 0.17
Nodes (23): _apply_branch_defaults(), _build_branch_defaults_from_vendor(), _consume_self_onboard_verification_token(), _get_branch_defaults_for_email(), get_branch_onboard_defaults(), _is_missing_payload_value(), _is_valid_email(), _normalize_email() (+15 more)

### Community 7 - "test_self_onboarding_flow.py"
Cohesion: 0.14
Nodes (13): _apply_slot_rows_for_day(), Slot, VendorDaySlotConfig, app(), MemoryRedis, payload(), fixture, Onboarding integration tests: real Flask/ORM, isolated DB, mocked external IO. (+5 more)

### Community 8 - "ConsolePricingOffer"
Cohesion: 0.28
Nodes (5): ConsolePricingOffer, Time-based promotional pricing for console types (AvailableGames) Allows…, Check if this offer is active RIGHT NOW using IST. Returns True if current IST…, Calculate discount percentage, Convert to dictionary for API responses

### Community 9 - "Image"
Cohesion: 0.40
Nodes (3): Image, Save image metadata to the database. Args: vendor_id (int): ID of the vendor…, Upload a single photo to Google Drive and return the file link.

### Community 10 - "OTPService"
Cohesion: 0.14
Nodes (9): OTPService, Verify the provided OTP - FAST, Check if vendor is already verified - INSTANT Just checks Redis - no database…, Send email asynchronously in background thread, Clear verification status, Clear all verification status for a vendor (for logout), Generate a random numeric OTP, Send OTP to vendor's email - OPTIMIZED FOR SPEED Returns immediately while… (+1 more)

### Community 11 - "replace_vendor_document"
Cohesion: 0.13
Nodes (14): _authorize_hours_owner(), cafe_requests(), delete_vendor_image(), delete_vendor_image_by_url(), Upload a missing (or replace existing) required onboarding document by…, Replace an existing vendor document file. Note: Replaced doc status becomes…, Deletes a vendor image from both Cloudinary and the database by image ID., Deletes a vendor image by URL from both Cloudinary and the database. (+6 more)

### Community 12 - "VendorService"
Cohesion: 0.23
Nodes (4): Creates a table for tracking vendor dashboard details., Creates a vendor-specific promo detail table., Safely parse date string, handling None and invalid values, VendorService

### Community 13 - ".search_gaming_cafes"
Cohesion: 0.22
Nodes (3): Retrieve all vendors with their statuses, timing info, amenities, images, and…, Lightweight app discovery search for cafes offering a game. Designed for high…, OPTIMIZED: Fetch payment methods for ALL vendors in a single query. Previously…

### Community 14 - "upload_photos"
Cohesion: 0.29
Nodes (5): API endpoint to upload photos to Google Drive., upload_photos(), Initialize and return the Google Drive service., Upload multiple photos to Google Drive and return their file links., Initialize and return the Google Drive service.

### Community 15 - "console_catalog"
Cohesion: 0.60
Nodes (5): console_catalog, games, game_console_catalog, game_discovery_events, game_popularity_rankings

### Community 16 - "services.py"
Cohesion: 0.05
Nodes (38): declared_attr, AdditionalDetails, Amenity, AvailableGame, BusinessRegistration, Console, ContactInfo, DocumentSubmitted (+30 more)

### Community 19 - ".send_welcome_email"
Cohesion: 0.33
Nodes (3): Send standardized onboarding email with vendor credentials., Build welcome email content fragment (wrapped by shared HFG template)., test_welcome_html_escapes_owner_data()

### Community 20 - ".extend_vendor_slot_window"
Cohesion: 0.12
Nodes (19): cron_extend_slots_for_all_active_cafes(), cron_extend_slots_for_vendor(), _ensure_vendor_slot_table_exists(), extend_slot_window(), _fetch_active_vendor_ids_for_slots(), _generate_blocks(), _is_valid_cron_request(), normalize_day_key() (+11 more)

### Community 32 - "test_operating_hours.py"
Cohesion: 0.22
Nodes (14): parametrize, Exercise the actual schedule handler/helpers with an isolated SQL database., save(), test_booking_conflict_detected_even_if_capacity_was_stale(), test_cafe_without_games_can_save_configuration(), test_capacity_is_preserved_and_conflicts_roll_back(), test_duplicate_template_cannot_delete_booked_slot_identity(), test_future_extension_uses_saved_weekday_grid_not_old_templates() (+6 more)

### Community 33 - "cafe_requests"
Cohesion: 0.50
Nodes (3): documents, cafe_requests, vendors

### Community 38 - "test_kiosk_releases.py"
Cohesion: 0.33
Nodes (3): parametrize, test_activation_preserves_current_version_when_download_is_private(), test_rejects_non_installer_and_credential_links()

### Community 41 - "_EmailText"
Cohesion: 0.29
Nodes (3): HTMLParser, _EmailText, Generate a useful plain-text alternative, retaining links and table values.

## Knowledge Gaps
- **5 isolated node(s):** `Invoice`, `kiosk_releases`, `graphify`, `Kiosk release management`, `Operating Hours save contract and release`
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VendorService` connect `VendorService` to `vendor_games.py`, `controllers.py`, `SuperAdminService`, `super_admin_controller.py`, `test_self_onboarding_flow.py`, `Image`, `.search_gaming_cafes`, `upload_photos`, `services.py`, `.send_deboard_notification`, `.send_welcome_email`, `.extend_vendor_slot_window`, `Document`, `.create_vendor_console_availability_table`, `.verify_document`, `.get_all_vendors_with_status`, `PaymentMethod`, `PaymentVendorMap`, `.get_unverified_documents`, `.verify_documents_and_update_vendor`?**
  _High betweenness centrality (0.202) - this node is a cross-community bridge._
- **Why does `SuperAdminService` connect `SuperAdminService` to `services.py`, `Document`, `super_admin_controller.py`, `VendorService`?**
  _High betweenness centrality (0.164) - this node is a cross-community bridge._
- **Why does `Vendor` connect `services.py` to `vendor_games.py`, `controllers.py`, `SuperAdminService`, `extensions.py`, `test_self_onboarding_flow.py`, `OTPService`, `VendorService`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SuperAdminService` (e.g. with `VendorService` and `ContactInfo`) actually correct?**
  _`SuperAdminService` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `VendorService` (e.g. with `AdditionalDetails` and `Amenity`) actually correct?**
  _`VendorService` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Invoice`, `kiosk_releases`, `graphify` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `vendor_games.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06612021857923497 - nodes in this community are weakly interconnected._