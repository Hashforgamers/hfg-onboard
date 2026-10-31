# Graph Report - hfg-onboard  (2026-10-06)

## Corpus Check
- 83 files · ~43,879 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 664 nodes · 1569 edges · 50 communities (34 shown, 16 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 85 edges (avg confidence: 0.54)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `72b5c6d0`
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
- services.py
- OTPService
- replace_vendor_document
- VendorService
- .search_gaming_cafes
- upload_photos
- console_catalog
- .onboard_vendor
- CloudinaryGameImageService
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
- Game
- cafe_requests
- test_operating_hours.py
- vendor.py
- 20261005_notification_context.sql
- GameService
- PaymentMethod
- operating-hours.md
- PaymentVendorMap
- build_hfg_email_html
- .create_game
- check_redis_health
- get_unverified_documents
- PasswordManager
- 20261005_kiosk_releases.sql
- create_redis_pool

## God Nodes (most connected - your core abstractions)
1. `SuperAdminService` - 80 edges
2. `VendorService` - 69 edges
3. `require_super_admin()` - 36 edges
4. `Vendor` - 32 edges
5. `build_hfg_email_html()` - 22 edges
6. `onboard_vendor()` - 17 edges
7. `GameService` - 17 edges
8. `CloudinaryGameImageService` - 15 edges
9. `MemoryRedis` - 14 edges
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

## Communities (50 total, 16 thin omitted)

### Community 0 - "vendor_games.py"
Cohesion: 0.20
Nodes (17): add_cover_image(), add_supported_game(), create_game(), create_games_batch(), delete_supported_game(), get_all_games(), health_check(), list_game_discovery_platforms() (+9 more)

### Community 1 - "order_controller.py"
Cohesion: 0.13
Nodes (25): add_product(), create_collaborator(), delete_collaborator(), delete_product(), list_collaborators(), list_products(), _notify_store_updated(), route (+17 more)

### Community 2 - "SuperAdminService"
Cohesion: 0.07
Nodes (4): Any, date, SuperAdminService, test_legacy_cron_refuses_overlapping_templates_without_config()

### Community 3 - "Flask"
Cohesion: 0.16
Nodes (8): Flask, Use the app's actual CORS configuration to test dashboard preflight., test_operating_hours_preflight_accepts_dashboard_headers(), ProxyTests, Verify the public kiosk proxy preserves authentication and API envelopes., parametrize, test_upstream_errors_identify_required_fix(), test_daily_cron_commits_each_cafe_without_full_capacity_repair()

### Community 4 - "super_admin_controller.py"
Cohesion: 0.10
Nodes (47): activate_kiosk_release(), change_subscription(), claim_early_onboard_promotion(), create_vendor_staff(), deboard_vendor_admin(), delete_subscription_model(), delete_vendor_staff(), get_daily_settlement_summary() (+39 more)

### Community 5 - "route"
Cohesion: 0.07
Nodes (28): check_verification(), get_all_gaming_cafe(), get_vendor_dashboard_data(), get_vendor_photos(), health_check(), insert_to_queue(), kiosk_next_slot_check_proxy(), kiosk_next_slot_confirm_proxy() (+20 more)

### Community 6 - "controllers.py"
Cohesion: 0.12
Nodes (35): allowed_file(), _apply_branch_defaults(), _build_branch_defaults_from_vendor(), cleanup_onboarding_documents(), _consume_self_onboard_verification_token(), _emit_unlock(), _get_branch_defaults_for_email(), get_branch_onboard_defaults() (+27 more)

### Community 7 - "test_self_onboarding_flow.py"
Cohesion: 0.09
Nodes (23): Config, create_app(), _is_insecure_secret(), _validate_production_config(), _apply_slot_rows_for_day(), Slot, app(), MemoryRedis (+15 more)

### Community 8 - ".to_dict"
Cohesion: 0.33
Nodes (3): Check if this offer is active RIGHT NOW using IST. Returns True if current IST…, Calculate discount percentage, Convert to dictionary for API responses

### Community 9 - "services.py"
Cohesion: 0.18
Nodes (5): datetime, ContactInfo, Transaction, VendorCredential, VendorPin

### Community 10 - "OTPService"
Cohesion: 0.14
Nodes (9): OTPService, Verify the provided OTP - FAST, Check if vendor is already verified - INSTANT Just checks Redis - no database…, Send email asynchronously in background thread, Clear verification status, Clear all verification status for a vendor (for logout), Generate a random numeric OTP, Send OTP to vendor's email - OPTIMIZED FOR SPEED Returns immediately while… (+1 more)

### Community 11 - "replace_vendor_document"
Cohesion: 0.13
Nodes (14): _authorize_hours_owner(), cafe_requests(), delete_vendor_image(), delete_vendor_image_by_url(), Upload a missing (or replace existing) required onboarding document by…, Replace an existing vendor document file. Note: Replaced doc status becomes…, Deletes a vendor image from both Cloudinary and the database by image ID., Deletes a vendor image by URL from both Cloudinary and the database. (+6 more)

### Community 12 - "VendorService"
Cohesion: 0.15
Nodes (8): deboard_vendor(), Document, Image, Save image metadata to the database. Args: vendor_id (int): ID of the vendor…, Upload a single photo to Google Drive and return the file link., Upload multiple photos to Google Drive and return their file links., Upload a file to Google Drive and return the file link., VendorService

### Community 13 - ".search_gaming_cafes"
Cohesion: 0.22
Nodes (3): Retrieve all vendors with their statuses, timing info, amenities, images, and…, Lightweight app discovery search for cafes offering a game. Designed for high…, OPTIMIZED: Fetch payment methods for ALL vendors in a single query. Previously…

### Community 14 - "upload_photos"
Cohesion: 0.40
Nodes (4): API endpoint to upload photos to Google Drive., upload_photos(), Initialize and return the Google Drive service., Initialize and return the Google Drive service.

### Community 15 - "console_catalog"
Cohesion: 0.60
Nodes (5): console_catalog, games, game_console_catalog, game_discovery_events, game_popularity_rankings

### Community 16 - ".onboard_vendor"
Cohesion: 0.09
Nodes (11): AdditionalDetails, Console, HardwareSpecification, MaintenanceStatus, PriceAndCost, VendorDaySlotConfig, Creates a table for tracking console availability for a vendor., Creates a table for tracking vendor dashboard details. (+3 more)

### Community 17 - "CloudinaryGameImageService"
Cohesion: 0.17
Nodes (8): CloudinaryGameImageService, Service for handling game cover images Images are uploaded to the 'poc' folder, Ultra-simple upload method as fallback, Delete a game cover image from Cloudinary, Checking if Cloudinary credentials are available, Initialize Cloudinary configuration, Upload collaborator product image to Cloudinary under folder…, Upload game cover image to Cloudinary 'poc' folder

### Community 19 - "AvailableGame"
Cohesion: 0.14
Nodes (9): AvailableGame, ConsolePricingOffer, Time-based promotional pricing for console types (AvailableGames) Allows…, Serialize VendorGame — price is always dynamically computed, Dynamically compute price from parent AvailableGame. - If an active…, Returns full pricing context: base price, offer price, offer details. Useful…, VendorGame, fixture (+1 more)

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

### Community 32 - "Game"
Cohesion: 0.20
Nodes (5): Game, Create Game from RAWG API - image_url gets background_image automatically!, PlatformEnum, SupportedGame, SupportedGameService

### Community 33 - "cafe_requests"
Cohesion: 0.50
Nodes (3): documents, cafe_requests, vendors

### Community 34 - "test_operating_hours.py"
Cohesion: 0.24
Nodes (13): parametrize, Exercise the actual schedule handler/helpers with an isolated SQL database., save(), test_booking_conflict_detected_even_if_capacity_was_stale(), test_cafe_without_games_can_save_configuration(), test_capacity_is_preserved_and_conflicts_roll_back(), test_duplicate_template_cannot_delete_booked_slot_identity(), test_future_extension_uses_saved_weekday_grid_not_old_templates() (+5 more)

### Community 35 - "vendor.py"
Cohesion: 0.18
Nodes (8): Amenity, BusinessRegistration, DocumentSubmitted, OpeningDay, PhysicalAddress, Timing, Vendor, VendorAccount

### Community 41 - "build_hfg_email_html"
Cohesion: 0.08
Nodes (19): HTMLParser, build_hfg_email_html(), email_text(), _EmailText, _extract_body(), Generate a useful plain-text alternative, retaining links and table values., Send invoice notification email with table format, Send standardized onboarding email with vendor credentials. (+11 more)

### Community 45 - "get_unverified_documents"
Cohesion: 0.50
Nodes (3): get_unverified_documents(), API endpoint to get all unverified document file paths for a given vendor., Fetch all unverified documents for the specified vendor.

### Community 46 - "PasswordManager"
Cohesion: 0.18
Nodes (6): declared_attr, PasswordManager, VendorStatus, Generate account credentials and notify vendor with login details., Update specified documents' status to 'verified' and set the vendor's status to…, generate_credentials()

## Knowledge Gaps
- **6 isolated node(s):** `Invoice`, `kiosk_releases`, `notification_campaign_settings`, `graphify`, `Kiosk release management` (+1 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VendorService` connect `VendorService` to `SuperAdminService`, `super_admin_controller.py`, `controllers.py`, `test_self_onboarding_flow.py`, `services.py`, `.search_gaming_cafes`, `upload_photos`, `.onboard_vendor`, `AvailableGame`, `.extend_vendor_slot_window`, `Booking`, `verify_document`, `get_vendor_dashboard`, `Game`, `vendor.py`, `PaymentMethod`, `PaymentVendorMap`, `build_hfg_email_html`, `get_unverified_documents`, `PasswordManager`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Why does `SuperAdminService` connect `SuperAdminService` to `vendor.py`, `super_admin_controller.py`, `services.py`, `VendorService`, `PasswordManager`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Why does `Vendor` connect `vendor.py` to `Game`, `order_controller.py`, `SuperAdminService`, `controllers.py`, `test_self_onboarding_flow.py`, `services.py`, `OTPService`, `VendorService`, `PasswordManager`, `.onboard_vendor`, `AvailableGame`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SuperAdminService` (e.g. with `VendorService` and `ContactInfo`) actually correct?**
  _`SuperAdminService` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `VendorService` (e.g. with `AdditionalDetails` and `Amenity`) actually correct?**
  _`VendorService` has 30 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Invoice`, `kiosk_releases`, `notification_campaign_settings` to the rest of the system?**
  _6 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `order_controller.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13015873015873017 - nodes in this community are weakly interconnected._