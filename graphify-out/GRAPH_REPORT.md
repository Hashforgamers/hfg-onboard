# Graph Report - hfg-onboard  (2026-10-04)

## Corpus Check
- 74 files · ~41,963 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 619 nodes · 1495 edges · 41 communities (27 shown, 14 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 82 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7d8ef54f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- vendor_games.py
- _apply_branch_defaults
- SuperAdminService
- order_controller.py
- super_admin_controller.py
- route
- onboard_vendor
- test_self_onboarding_flow.py
- .to_dict
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
- .generate_credentials_and_notify
- allowed_file
- .handle_documents
- AGENTS.md
- kiosk_next_slot_confirm_proxy
- controllers.py
- .create_vendor_console_availability_table
- DocumentReviewTests
- .verify_document
- .get_all_vendors_with_status
- password_manager
- Flask
- cafe_requests
- .create_vendor_dashboard_table
- .create_vendor_promo_table
- .safe_strptime
- operating-hours.md
- Document
- _EmailText

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

## Communities (41 total, 14 thin omitted)

### Community 0 - "vendor_games.py"
Cohesion: 0.06
Nodes (32): add_cover_image(), add_supported_game(), create_game(), create_games_batch(), delete_supported_game(), get_all_games(), health_check(), list_game_discovery_platforms() (+24 more)

### Community 1 - "_apply_branch_defaults"
Cohesion: 0.32
Nodes (8): _apply_branch_defaults(), _build_branch_defaults_from_vendor(), _get_branch_defaults_for_email(), get_branch_onboard_defaults(), _is_missing_payload_value(), _normalize_cafe_name(), _normalize_whitespace(), Return reusable onboarding defaults for adding a new branch under an existing…

### Community 2 - "SuperAdminService"
Cohesion: 0.07
Nodes (4): Any, date, SuperAdminService, test_legacy_cron_refuses_overlapping_templates_without_config()

### Community 3 - "order_controller.py"
Cohesion: 0.12
Nodes (26): add_product(), create_collaborator(), delete_collaborator(), delete_product(), list_collaborators(), list_products(), _notify_store_updated(), route (+18 more)

### Community 4 - "super_admin_controller.py"
Cohesion: 0.13
Nodes (38): change_subscription(), claim_early_onboard_promotion(), create_vendor_staff(), deboard_vendor_admin(), delete_subscription_model(), delete_vendor_staff(), get_daily_settlement_summary(), get_vendor() (+30 more)

### Community 5 - "route"
Cohesion: 0.06
Nodes (33): check_verification(), deboard_vendor(), extend_slot_window(), get_all_gaming_cafe(), get_unverified_documents(), get_vendor_dashboard(), get_vendor_dashboard_data(), health_check() (+25 more)

### Community 6 - "onboard_vendor"
Cohesion: 0.18
Nodes (19): _consume_self_onboard_verification_token(), _is_valid_email(), _normalize_email(), _normalize_phone(), onboard_vendor(), Validate the JSON data for required fields., Safely parse date string, handling None and invalid values, safe_strptime() (+11 more)

### Community 7 - "test_self_onboarding_flow.py"
Cohesion: 0.08
Nodes (29): _apply_slot_rows_for_day(), cron_extend_slots_for_all_active_cafes(), cron_extend_slots_for_vendor(), _ensure_vendor_slot_table_exists(), _fetch_active_vendor_ids_for_slots(), _generate_blocks(), _is_valid_cron_request(), normalize_day_key() (+21 more)

### Community 8 - ".to_dict"
Cohesion: 0.33
Nodes (3): Check if this offer is active RIGHT NOW using IST. Returns True if current IST…, Calculate discount percentage, Convert to dictionary for API responses

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
Cohesion: 0.29
Nodes (3): Fetch all unverified documents for the specified vendor., Update specified documents' status to 'verified' and set the vendor's status to…, VendorService

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
Nodes (41): datetime, check_redis_health(), create_redis_pool(), Create a Redis connection pool to reuse connections This prevents repeated SSL…, Check Redis connection health, declared_attr, AdditionalDetails, Amenity (+33 more)

### Community 19 - ".generate_credentials_and_notify"
Cohesion: 0.25
Nodes (4): Send standardized onboarding email with vendor credentials., Build welcome email content fragment (wrapped by shared HFG template)., Generate account credentials and notify vendor with login details., test_welcome_html_escapes_owner_data()

### Community 20 - "allowed_file"
Cohesion: 0.50
Nodes (4): allowed_file(), format_filename(), Check if the file has an allowed extension., Format the filename as…

### Community 24 - "controllers.py"
Cohesion: 0.17
Nodes (10): allowed_file(), _emit_unlock(), get_vendor_photos(), API endpoint to retrieve all photos for a given vendor ID. Args: vendor_id…, Emit unlock signal to internal WebSocket service, # IMPORTANT: Fetch real documents from your Document model, Check if the file has an allowed extension., AccessBookingCode (+2 more)

### Community 32 - "Flask"
Cohesion: 0.08
Nodes (25): Config, create_app(), _is_insecure_secret(), _validate_production_config(), Flask, parametrize, Use the app's actual CORS configuration to test dashboard preflight., test_operating_hours_preflight_accepts_dashboard_headers() (+17 more)

### Community 33 - "cafe_requests"
Cohesion: 0.50
Nodes (3): documents, cafe_requests, vendors

### Community 40 - "Document"
Cohesion: 0.50
Nodes (3): Save uploaded document metadata once; avoid duplicate inserts and loop commits., save_vendor_documents(), Document

### Community 41 - "_EmailText"
Cohesion: 0.29
Nodes (3): HTMLParser, _EmailText, Generate a useful plain-text alternative, retaining links and table values.

## Knowledge Gaps
- **3 isolated node(s):** `Invoice`, `graphify`, `Operating Hours save contract and release`
  These have ≤1 connection - possible missing edges or undocumented components.
- **14 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VendorService` connect `VendorService` to `vendor_games.py`, `SuperAdminService`, `super_admin_controller.py`, `test_self_onboarding_flow.py`, `Image`, `.search_gaming_cafes`, `upload_photos`, `services.py`, `.send_deboard_notification`, `.generate_credentials_and_notify`, `.handle_documents`, `controllers.py`, `.create_vendor_console_availability_table`, `.verify_document`, `.get_all_vendors_with_status`, `.create_vendor_dashboard_table`, `.create_vendor_promo_table`, `.safe_strptime`, `Document`?**
  _High betweenness centrality (0.208) - this node is a cross-community bridge._
- **Why does `SuperAdminService` connect `SuperAdminService` to `services.py`, `Document`, `super_admin_controller.py`, `VendorService`?**
  _High betweenness centrality (0.170) - this node is a cross-community bridge._
- **Why does `Vendor` connect `services.py` to `vendor_games.py`, `Flask`, `SuperAdminService`, `order_controller.py`, `test_self_onboarding_flow.py`, `OTPService`, `VendorService`, `controllers.py`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SuperAdminService` (e.g. with `VendorService` and `ContactInfo`) actually correct?**
  _`SuperAdminService` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `VendorService` (e.g. with `AdditionalDetails` and `Amenity`) actually correct?**
  _`VendorService` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Invoice`, `graphify`, `Operating Hours save contract and release` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `vendor_games.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06498015873015874 - nodes in this community are weakly interconnected._