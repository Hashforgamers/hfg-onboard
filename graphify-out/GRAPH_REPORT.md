# Graph Report - hfg-onboard  (2026-10-03)

## Corpus Check
- 71 files · ~41,256 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 607 nodes · 1477 edges · 41 communities (26 shown, 15 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 79 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0ae56e16`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- vendor_games.py
- services.py
- SuperAdminService
- order_controller.py
- super_admin_controller.py
- route
- onboard_vendor
- controllers.py
- ConsolePricingOffer
- .extend_vendor_slot_window
- OTPService
- replace_vendor_document
- VendorService
- .search_gaming_cafes
- upload_photos
- console_catalog
- .send_welcome_email
- Image
- CatalogProxyTests
- test_self_onboarding_flow.py
- .create_vendor_console_availability_table
- .create_vendor_dashboard_table
- AGENTS.md
- _EmailText
- Booking
- .get_unverified_documents
- DocumentReviewTests
- .verify_document
- .get_all_vendors_with_status
- password_manager
- .send_deboard_notification
- cafe_requests
- .safe_strptime
- .create_vendor_promo_table
- .verify_documents_and_update_vendor
- test_operating_hours.py
- operating-hours.md
- Document
- allowed_file

## God Nodes (most connected - your core abstractions)
1. `SuperAdminService` - 80 edges
2. `VendorService` - 69 edges
3. `require_super_admin()` - 32 edges
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
- `setup()` --calls--> `AvailableGame`  [INFERRED]
  tests/test_operating_hours.py → models/availableGame.py
- `VendorService` --uses--> `Booking`  [INFERRED]
  services/services.py → models/booking.py

## Import Cycles
- None detected.

## Communities (41 total, 15 thin omitted)

### Community 0 - "vendor_games.py"
Cohesion: 0.06
Nodes (32): add_cover_image(), add_supported_game(), create_game(), create_games_batch(), delete_supported_game(), get_all_games(), health_check(), list_game_discovery_platforms() (+24 more)

### Community 1 - "services.py"
Cohesion: 0.05
Nodes (40): datetime, check_redis_health(), create_redis_pool(), Create a Redis connection pool to reuse connections This prevents repeated SSL…, Check Redis connection health, declared_attr, AdditionalDetails, Amenity (+32 more)

### Community 2 - "SuperAdminService"
Cohesion: 0.07
Nodes (3): Any, date, SuperAdminService

### Community 3 - "order_controller.py"
Cohesion: 0.07
Nodes (33): Config, create_app(), _is_insecure_secret(), _validate_production_config(), add_product(), create_collaborator(), delete_collaborator(), delete_product() (+25 more)

### Community 4 - "super_admin_controller.py"
Cohesion: 0.13
Nodes (38): change_subscription(), claim_early_onboard_promotion(), create_vendor_staff(), deboard_vendor_admin(), delete_subscription_model(), delete_vendor_staff(), get_daily_settlement_summary(), get_vendor() (+30 more)

### Community 5 - "route"
Cohesion: 0.06
Nodes (34): check_verification(), get_all_gaming_cafe(), get_unverified_documents(), get_vendor_dashboard(), get_vendor_dashboard_data(), get_vendor_photos(), health_check(), insert_to_queue() (+26 more)

### Community 6 - "onboard_vendor"
Cohesion: 0.17
Nodes (19): _apply_branch_defaults(), _build_branch_defaults_from_vendor(), _consume_self_onboard_verification_token(), _get_branch_defaults_for_email(), get_branch_onboard_defaults(), _is_missing_payload_value(), _normalize_cafe_name(), _normalize_email() (+11 more)

### Community 7 - "controllers.py"
Cohesion: 0.22
Nodes (14): allowed_file(), _emit_unlock(), _is_valid_email(), _normalize_phone(), Emit unlock signal to internal WebSocket service, # IMPORTANT: Fetch real documents from your Document model, Check if the file has an allowed extension., _self_onboard_duplicate_reason() (+6 more)

### Community 8 - "ConsolePricingOffer"
Cohesion: 0.28
Nodes (5): ConsolePricingOffer, Time-based promotional pricing for console types (AvailableGames) Allows…, Check if this offer is active RIGHT NOW using IST. Returns True if current IST…, Calculate discount percentage, Convert to dictionary for API responses

### Community 9 - ".extend_vendor_slot_window"
Cohesion: 0.12
Nodes (19): cron_extend_slots_for_all_active_cafes(), cron_extend_slots_for_vendor(), _ensure_vendor_slot_table_exists(), extend_slot_window(), _fetch_active_vendor_ids_for_slots(), _generate_blocks(), _is_valid_cron_request(), normalize_day_key() (+11 more)

### Community 10 - "OTPService"
Cohesion: 0.14
Nodes (9): OTPService, Verify the provided OTP - FAST, Check if vendor is already verified - INSTANT Just checks Redis - no database…, Send email asynchronously in background thread, Clear verification status, Clear all verification status for a vendor (for logout), Generate a random numeric OTP, Send OTP to vendor's email - OPTIMIZED FOR SPEED Returns immediately while… (+1 more)

### Community 11 - "replace_vendor_document"
Cohesion: 0.13
Nodes (14): _authorize_hours_owner(), cafe_requests(), delete_vendor_image(), delete_vendor_image_by_url(), Upload a missing (or replace existing) required onboarding document by…, Replace an existing vendor document file. Note: Replaced doc status becomes…, Deletes a vendor image from both Cloudinary and the database by image ID., Deletes a vendor image by URL from both Cloudinary and the database. (+6 more)

### Community 12 - "VendorService"
Cohesion: 0.31
Nodes (3): deboard_vendor(), Upload a file to Google Drive and return the file link., VendorService

### Community 13 - ".search_gaming_cafes"
Cohesion: 0.22
Nodes (3): Retrieve all vendors with their statuses, timing info, amenities, images, and…, Lightweight app discovery search for cafes offering a game. Designed for high…, OPTIMIZED: Fetch payment methods for ALL vendors in a single query. Previously…

### Community 14 - "upload_photos"
Cohesion: 0.29
Nodes (5): API endpoint to upload photos to Google Drive., upload_photos(), Initialize and return the Google Drive service., Upload multiple photos to Google Drive and return their file links., Initialize and return the Google Drive service.

### Community 15 - "console_catalog"
Cohesion: 0.60
Nodes (5): console_catalog, games, game_console_catalog, game_discovery_events, game_popularity_rankings

### Community 16 - ".send_welcome_email"
Cohesion: 0.33
Nodes (3): Send standardized onboarding email with vendor credentials., Build welcome email content fragment (wrapped by shared HFG template)., test_welcome_html_escapes_owner_data()

### Community 17 - "Image"
Cohesion: 0.40
Nodes (3): Image, Save image metadata to the database. Args: vendor_id (int): ID of the vendor…, Upload a single photo to Google Drive and return the file link.

### Community 19 - "test_self_onboarding_flow.py"
Cohesion: 0.16
Nodes (12): _apply_slot_rows_for_day(), Slot, app(), MemoryRedis, payload(), fixture, Onboarding integration tests: real Flask/ORM, isolated DB, mocked external IO., submit() (+4 more)

### Community 23 - "_EmailText"
Cohesion: 0.29
Nodes (3): HTMLParser, _EmailText, Generate a useful plain-text alternative, retaining links and table values.

### Community 33 - "cafe_requests"
Cohesion: 0.50
Nodes (3): documents, cafe_requests, vendors

### Community 37 - "test_operating_hours.py"
Cohesion: 0.23
Nodes (12): parametrize, fixture, Exercise the actual schedule handler/helpers with an isolated SQL database., save(), setup(), test_booking_conflict_detected_even_if_capacity_was_stale(), test_cafe_without_games_can_save_configuration(), test_capacity_is_preserved_and_conflicts_roll_back() (+4 more)

### Community 40 - "Document"
Cohesion: 0.50
Nodes (3): Save uploaded document metadata once; avoid duplicate inserts and loop commits., save_vendor_documents(), Document

### Community 41 - "allowed_file"
Cohesion: 0.50
Nodes (4): allowed_file(), format_filename(), Check if the file has an allowed extension., Format the filename as…

## Knowledge Gaps
- **3 isolated node(s):** `Invoice`, `graphify`, `Operating Hours save contract and release`
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VendorService` connect `VendorService` to `vendor_games.py`, `services.py`, `SuperAdminService`, `super_admin_controller.py`, `controllers.py`, `.extend_vendor_slot_window`, `.search_gaming_cafes`, `upload_photos`, `.send_welcome_email`, `Image`, `test_self_onboarding_flow.py`, `.create_vendor_console_availability_table`, `.create_vendor_dashboard_table`, `Booking`, `.get_unverified_documents`, `.verify_document`, `.get_all_vendors_with_status`, `.send_deboard_notification`, `.safe_strptime`, `.create_vendor_promo_table`, `.verify_documents_and_update_vendor`, `Document`?**
  _High betweenness centrality (0.214) - this node is a cross-community bridge._
- **Why does `SuperAdminService` connect `SuperAdminService` to `Document`, `services.py`, `super_admin_controller.py`, `VendorService`?**
  _High betweenness centrality (0.174) - this node is a cross-community bridge._
- **Why does `Vendor` connect `services.py` to `vendor_games.py`, `SuperAdminService`, `order_controller.py`, `test_operating_hours.py`, `controllers.py`, `OTPService`, `VendorService`, `test_self_onboarding_flow.py`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SuperAdminService` (e.g. with `VendorService` and `ContactInfo`) actually correct?**
  _`SuperAdminService` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `VendorService` (e.g. with `AdditionalDetails` and `Amenity`) actually correct?**
  _`VendorService` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Invoice`, `graphify`, `Operating Hours save contract and release` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `vendor_games.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06498015873015874 - nodes in this community are weakly interconnected._