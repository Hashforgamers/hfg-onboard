# Graph Report - hfg-onboard  (2026-10-06)

## Corpus Check
- 82 files · ~43,674 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 662 nodes · 1564 edges · 43 communities (31 shown, 12 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 84 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2d6e214c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- vendor_games.py
- order_controller.py
- SuperAdminService
- Flask
- super_admin_controller.py
- route
- controllers.py
- test_self_onboarding_flow.py
- .to_dict
- extensions.py
- OTPService
- replace_vendor_document
- VendorService
- .search_gaming_cafes
- upload_photos
- console_catalog
- services.py
- .send_deboard_notification
- CatalogProxyTests
- AvailableGame
- .extend_vendor_slot_window
- test_kiosk_releases.py
- AGENTS.md
- kiosk-releases.md
- test_notification_context.py
- Booking
- DocumentReviewTests
- verify_document
- get_vendor_dashboard
- password_manager
- allowed_file
- cafe_requests
- Vendor
- 20261005_notification_context.sql
- allowed_file
- operating-hours.md
- email_template.py
- get_unverified_documents
- PasswordManager
- 20261005_kiosk_releases.sql

## God Nodes (most connected - your core abstractions)
1. `SuperAdminService` - 80 edges
2. `VendorService` - 69 edges
3. `require_super_admin()` - 36 edges
4. `Vendor` - 32 edges
5. `build_hfg_email_html()` - 22 edges
6. `onboard_vendor()` - 17 edges
7. `GameService` - 17 edges
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

## Communities (43 total, 12 thin omitted)

### Community 0 - "vendor_games.py"
Cohesion: 0.06
Nodes (32): add_cover_image(), add_supported_game(), create_game(), create_games_batch(), delete_supported_game(), get_all_games(), health_check(), list_game_discovery_platforms() (+24 more)

### Community 1 - "order_controller.py"
Cohesion: 0.12
Nodes (26): add_product(), create_collaborator(), delete_collaborator(), delete_product(), list_collaborators(), list_products(), _notify_store_updated(), route (+18 more)

### Community 2 - "SuperAdminService"
Cohesion: 0.07
Nodes (5): Any, date, build_hfg_email_html(), SuperAdminService, test_legacy_cron_refuses_overlapping_templates_without_config()

### Community 3 - "Flask"
Cohesion: 0.07
Nodes (27): Config, create_app(), _is_insecure_secret(), _validate_production_config(), Flask, Use the app's actual CORS configuration to test dashboard preflight., test_operating_hours_preflight_accepts_dashboard_headers(), ProxyTests (+19 more)

### Community 4 - "super_admin_controller.py"
Cohesion: 0.11
Nodes (47): activate_kiosk_release(), change_subscription(), claim_early_onboard_promotion(), create_vendor_staff(), deboard_vendor_admin(), delete_subscription_model(), delete_vendor_staff(), get_daily_settlement_summary() (+39 more)

### Community 5 - "route"
Cohesion: 0.07
Nodes (28): check_verification(), get_all_gaming_cafe(), get_vendor_dashboard_data(), get_vendor_photos(), health_check(), insert_to_queue(), kiosk_next_slot_check_proxy(), kiosk_next_slot_confirm_proxy() (+20 more)

### Community 6 - "controllers.py"
Cohesion: 0.12
Nodes (35): _apply_branch_defaults(), _build_branch_defaults_from_vendor(), cleanup_onboarding_documents(), _consume_self_onboard_verification_token(), _emit_unlock(), _get_branch_defaults_for_email(), get_branch_onboard_defaults(), _is_missing_payload_value() (+27 more)

### Community 7 - "test_self_onboarding_flow.py"
Cohesion: 0.10
Nodes (21): _apply_slot_rows_for_day(), Slot, Send standardized onboarding email with vendor credentials., Build welcome email content fragment (wrapped by shared HFG template)., app(), MemoryRedis, payload(), fixture (+13 more)

### Community 8 - ".to_dict"
Cohesion: 0.33
Nodes (3): Check if this offer is active RIGHT NOW using IST. Returns True if current IST…, Calculate discount percentage, Convert to dictionary for API responses

### Community 9 - "extensions.py"
Cohesion: 0.15
Nodes (10): datetime, check_redis_health(), create_redis_pool(), Create a Redis connection pool to reuse connections This prevents repeated SSL…, Check Redis connection health, ContactInfo, DocumentSubmitted, PhysicalAddress (+2 more)

### Community 10 - "OTPService"
Cohesion: 0.14
Nodes (9): OTPService, Verify the provided OTP - FAST, Check if vendor is already verified - INSTANT Just checks Redis - no database…, Send email asynchronously in background thread, Clear verification status, Clear all verification status for a vendor (for logout), Generate a random numeric OTP, Send OTP to vendor's email - OPTIMIZED FOR SPEED Returns immediately while… (+1 more)

### Community 11 - "replace_vendor_document"
Cohesion: 0.13
Nodes (14): _authorize_hours_owner(), cafe_requests(), delete_vendor_image(), delete_vendor_image_by_url(), Upload a missing (or replace existing) required onboarding document by…, Replace an existing vendor document file. Note: Replaced doc status becomes…, Deletes a vendor image from both Cloudinary and the database by image ID., Deletes a vendor image by URL from both Cloudinary and the database. (+6 more)

### Community 12 - "VendorService"
Cohesion: 0.11
Nodes (10): deboard_vendor(), Document, PaymentMethod, PaymentVendorMap, Image, Save image metadata to the database. Args: vendor_id (int): ID of the vendor…, Upload a single photo to Google Drive and return the file link., Upload multiple photos to Google Drive and return their file links. (+2 more)

### Community 13 - ".search_gaming_cafes"
Cohesion: 0.22
Nodes (3): Retrieve all vendors with their statuses, timing info, amenities, images, and…, Lightweight app discovery search for cafes offering a game. Designed for high…, OPTIMIZED: Fetch payment methods for ALL vendors in a single query. Previously…

### Community 14 - "upload_photos"
Cohesion: 0.40
Nodes (4): API endpoint to upload photos to Google Drive., upload_photos(), Initialize and return the Google Drive service., Initialize and return the Google Drive service.

### Community 15 - "console_catalog"
Cohesion: 0.60
Nodes (5): console_catalog, games, game_console_catalog, game_discovery_events, game_popularity_rankings

### Community 16 - "services.py"
Cohesion: 0.12
Nodes (10): AdditionalDetails, Console, MaintenanceStatus, PriceAndCost, VendorCredential, VendorDaySlotConfig, VendorPin, generate_credentials() (+2 more)

### Community 19 - "AvailableGame"
Cohesion: 0.16
Nodes (7): AvailableGame, ConsolePricingOffer, Time-based promotional pricing for console types (AvailableGames) Allows…, Serialize VendorGame — price is always dynamically computed, Dynamically compute price from parent AvailableGame. - If an active…, Returns full pricing context: base price, offer price, offer details. Useful…, VendorGame

### Community 20 - ".extend_vendor_slot_window"
Cohesion: 0.12
Nodes (19): cron_extend_slots_for_all_active_cafes(), cron_extend_slots_for_vendor(), _ensure_vendor_slot_table_exists(), extend_slot_window(), _fetch_active_vendor_ids_for_slots(), _generate_blocks(), _is_valid_cron_request(), normalize_day_key() (+11 more)

### Community 21 - "test_kiosk_releases.py"
Cohesion: 0.27
Nodes (5): parametrize, test_activation_preserves_current_version_when_download_is_private(), test_drive_installer_without_github_source(), test_rejects_invalid_drive_links(), test_rejects_non_installer_and_credential_links()

### Community 27 - "verify_document"
Cohesion: 0.50
Nodes (3): API endpoint to mark a document as verified and update vendor status if…, verify_document(), Mark a document as verified and set the vendor's status to active if all…

### Community 28 - "get_vendor_dashboard"
Cohesion: 0.50
Nodes (3): get_vendor_dashboard(), API to retrieve all vendors with their statuses and relevant information for…, Retrieve all vendors with their statuses, timing info, and relevant information…

### Community 32 - "allowed_file"
Cohesion: 0.50
Nodes (4): allowed_file(), format_filename(), Check if the file has an allowed extension., Format the filename as…

### Community 33 - "cafe_requests"
Cohesion: 0.50
Nodes (3): documents, cafe_requests, vendors

### Community 35 - "Vendor"
Cohesion: 0.12
Nodes (10): Amenity, BusinessRegistration, HardwareSpecification, OpeningDay, Timing, Vendor, Creates a table for tracking console availability for a vendor., Creates a table for tracking vendor dashboard details. (+2 more)

### Community 41 - "email_template.py"
Cohesion: 0.24
Nodes (5): HTMLParser, email_text(), _EmailText, _extract_body(), Generate a useful plain-text alternative, retaining links and table values.

### Community 45 - "get_unverified_documents"
Cohesion: 0.50
Nodes (3): get_unverified_documents(), API endpoint to get all unverified document file paths for a given vendor., Fetch all unverified documents for the specified vendor.

### Community 46 - "PasswordManager"
Cohesion: 0.20
Nodes (5): declared_attr, PasswordManager, VendorStatus, Generate account credentials and notify vendor with login details., Update specified documents' status to 'verified' and set the vendor's status to…

## Knowledge Gaps
- **6 isolated node(s):** `Invoice`, `kiosk_releases`, `notification_campaign_settings`, `graphify`, `Kiosk release management` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VendorService` connect `VendorService` to `vendor_games.py`, `SuperAdminService`, `Vendor`, `super_admin_controller.py`, `controllers.py`, `test_self_onboarding_flow.py`, `extensions.py`, `.search_gaming_cafes`, `PasswordManager`, `upload_photos`, `services.py`, `.send_deboard_notification`, `get_unverified_documents`, `AvailableGame`, `.extend_vendor_slot_window`, `Booking`, `verify_document`, `get_vendor_dashboard`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `SuperAdminService` connect `SuperAdminService` to `Vendor`, `super_admin_controller.py`, `extensions.py`, `VendorService`, `PasswordManager`, `services.py`?**
  _High betweenness centrality (0.157) - this node is a cross-community bridge._
- **Why does `Vendor` connect `Vendor` to `vendor_games.py`, `order_controller.py`, `SuperAdminService`, `Flask`, `controllers.py`, `test_self_onboarding_flow.py`, `extensions.py`, `OTPService`, `VendorService`, `PasswordManager`, `services.py`, `AvailableGame`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SuperAdminService` (e.g. with `VendorService` and `ContactInfo`) actually correct?**
  _`SuperAdminService` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `VendorService` (e.g. with `AdditionalDetails` and `Amenity`) actually correct?**
  _`VendorService` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Invoice`, `kiosk_releases`, `notification_campaign_settings` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `vendor_games.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06498015873015874 - nodes in this community are weakly interconnected._