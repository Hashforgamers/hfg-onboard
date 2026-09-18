# Graph Report - hfg-onboard  (2026-08-01)

## Corpus Check
- 64 files · ~36,363 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 526 nodes · 1294 edges · 32 communities (19 shown, 13 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 67 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7800f9c2`
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
- VendorGame
- cron_extend_slots_for_all_active_cafes
- OTPService
- upload_vendor_missing_document
- VendorService
- .search_gaming_cafes
- upload_photos
- console_catalog
- Document
- Image
- .send_welcome_email
- .send_deboard_notification
- PaymentMethod
- PaymentVendorMap
- AGENTS.md
- validate_json
- .create_vendor_dashboard_table
- .create_vendor_promo_table
- .safe_strptime
- .verify_document
- .get_all_vendors_with_status
- password_manager

## God Nodes (most connected - your core abstractions)
1. `SuperAdminService` - 70 edges
2. `VendorService` - 68 edges
3. `require_super_admin()` - 29 edges
4. `Vendor` - 29 edges
5. `build_hfg_email_html()` - 22 edges
6. `GameService` - 17 edges
7. `CloudinaryGameImageService` - 15 edges
8. `onboard_vendor()` - 14 edges
9. `Game` - 12 edges
10. `VendorStatus` - 12 edges

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

## Communities (32 total, 13 thin omitted)

### Community 0 - "vendor_games.py"
Cohesion: 0.06
Nodes (37): Config, create_app(), _is_insecure_secret(), _validate_production_config(), add_cover_image(), add_supported_game(), create_game(), create_games_batch() (+29 more)

### Community 1 - "services.py"
Cohesion: 0.07
Nodes (31): declared_attr, AdditionalDetails, Amenity, AvailableGame, BusinessRegistration, Console, ContactInfo, DocumentSubmitted (+23 more)

### Community 2 - "SuperAdminService"
Cohesion: 0.08
Nodes (3): Any, date, SuperAdminService

### Community 3 - "extensions.py"
Cohesion: 0.08
Nodes (33): add_product(), create_collaborator(), delete_collaborator(), delete_product(), list_collaborators(), list_products(), _notify_store_updated(), route (+25 more)

### Community 4 - "super_admin_controller.py"
Cohesion: 0.14
Nodes (36): change_subscription(), claim_early_onboard_promotion(), create_vendor_staff(), deboard_vendor_admin(), delete_vendor_staff(), get_daily_settlement_summary(), get_vendor(), get_vendor_subscriptions() (+28 more)

### Community 5 - "route"
Cohesion: 0.06
Nodes (35): check_verification(), deboard_vendor(), get_all_gaming_cafe(), get_unverified_documents(), get_vendor_dashboard(), get_vendor_dashboard_data(), get_vendor_photos(), health_check() (+27 more)

### Community 6 - "onboard_vendor"
Cohesion: 0.17
Nodes (23): _apply_branch_defaults(), _build_branch_defaults_from_vendor(), _consume_self_onboard_verification_token(), _get_branch_defaults_for_email(), get_branch_onboard_defaults(), _is_missing_payload_value(), _is_valid_email(), _normalize_cafe_name() (+15 more)

### Community 7 - "controllers.py"
Cohesion: 0.12
Nodes (17): allowed_file(), _apply_slot_rows_for_day(), _emit_unlock(), _generate_blocks(), normalize_day_key(), parse_time_flexible(), Emit unlock signal to internal WebSocket service, # IMPORTANT: Fetch real documents from your Document model (+9 more)

### Community 8 - "VendorGame"
Cohesion: 0.13
Nodes (9): ConsolePricingOffer, Time-based promotional pricing for console types (AvailableGames) Allows…, Check if this offer is active RIGHT NOW using IST. Returns True if current IST…, Calculate discount percentage, Convert to dictionary for API responses, Serialize VendorGame — price is always dynamically computed, Dynamically compute price from parent AvailableGame. - If an active…, Returns full pricing context: base price, offer price, offer details. Useful… (+1 more)

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
Cohesion: 0.21
Nodes (4): Creates a table for tracking console availability for a vendor., Fetch all unverified documents for the specified vendor., Update specified documents' status to 'verified' and set the vendor's status to…, VendorService

### Community 13 - ".search_gaming_cafes"
Cohesion: 0.22
Nodes (3): Retrieve all vendors with their statuses, timing info, amenities, images, and…, Lightweight app discovery search for cafes offering a game. Designed for high…, OPTIMIZED: Fetch payment methods for ALL vendors in a single query. Previously…

### Community 14 - "upload_photos"
Cohesion: 0.29
Nodes (5): API endpoint to upload photos to Google Drive., upload_photos(), Initialize and return the Google Drive service., Upload multiple photos to Google Drive and return their file links., Initialize and return the Google Drive service.

### Community 15 - "console_catalog"
Cohesion: 0.60
Nodes (5): console_catalog, games, game_console_catalog, game_discovery_events, game_popularity_rankings

### Community 17 - "Image"
Cohesion: 0.40
Nodes (3): Image, Save image metadata to the database. Args: vendor_id (int): ID of the vendor…, Upload a single photo to Google Drive and return the file link.

## Knowledge Gaps
- **2 isolated node(s):** `Invoice`, `graphify`
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `VendorService` connect `VendorService` to `vendor_games.py`, `services.py`, `SuperAdminService`, `extensions.py`, `super_admin_controller.py`, `controllers.py`, `VendorGame`, `cron_extend_slots_for_all_active_cafes`, `.search_gaming_cafes`, `upload_photos`, `Document`, `Image`, `.send_welcome_email`, `.send_deboard_notification`, `PaymentMethod`, `PaymentVendorMap`, `.create_vendor_dashboard_table`, `.create_vendor_promo_table`, `.safe_strptime`, `.verify_document`, `.get_all_vendors_with_status`?**
  _High betweenness centrality (0.252) - this node is a cross-community bridge._
- **Why does `SuperAdminService` connect `SuperAdminService` to `Document`, `services.py`, `super_admin_controller.py`, `VendorService`?**
  _High betweenness centrality (0.174) - this node is a cross-community bridge._
- **Why does `Vendor` connect `services.py` to `vendor_games.py`, `SuperAdminService`, `extensions.py`, `controllers.py`, `OTPService`, `VendorService`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `SuperAdminService` (e.g. with `VendorService` and `ContactInfo`) actually correct?**
  _`SuperAdminService` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `VendorService` (e.g. with `AdditionalDetails` and `Amenity`) actually correct?**
  _`VendorService` has 29 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Invoice`, `graphify` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `vendor_games.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05516475379489078 - nodes in this community are weakly interconnected._