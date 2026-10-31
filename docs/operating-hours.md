# Operating Hours save contract and release

Account Settings → Operating Hours uses `POST /api/vendor/{vendor_id}/updateSlot` on hfg-onboard, and loads saved settings through the dashboard service's `GET /api/vendor/{vendor_id}/dashboard`.

Deploy hfg-onboard and hfg-dashboard-service before hash-dashboard. Install the updated hfg-onboard requirements (PyJWT) and configure its `JWT_SECRET_KEY` to match the owner login service. Saves require the cafe owner's existing login JWT, with `sub.type=vendor` and the matching `sub.id`; the frontend already sends it. Missing/expired tokens return 401, a different cafe returns 403, and an unconfigured signing key returns 503. The save transaction creates four `vendor_operating_schedule_*` tables and an inventory trigger as needed. The database role must be able to create tables, a trigger function, and triggers. Deploy the hfg-booking changes before enabling this save behavior so slot readers and booking preflight respect disabled inventory.

The request includes day, start_time, end_time, integer slot_duration (15–240 minutes), boolean is_enabled and is_24_hours, and optional window_days (1–365). The dashboard sends a 14-day generation window; existing future inventory for the same weekday is also updated beyond that window. Times accept HH:MM or HH:MM AM/PM. Overnight and 24-hour windows are supported. An enabled window must fit at least one full slot. Partial trailing minutes are not offered as a shorter slot.

The successful response now includes `operatingHours` with the canonical saved row: day, open, close, slotDurationMinutes, isEnabled and is24Hours. The editor uses this as its saved/cancel baseline. Errors retain the draft and display the server message. All seven weekdays are returned by the read API; missing days in a partial opening_days configuration are closed.

Saving no longer deletes and recreates matching inventory at full capacity. Existing slot capacities are preserved. Owners may shorten hours, close a day, or change slot duration at any time. Booked/held inventory outside the new grid is retained with its identity and capacity intact but closed to new bookings. Existing bookings and QR reservations are not cancelled. The response reports `preserved_slots`, and the dashboard shows this count. A database allowlist prevents cancellation, capacity release, or historical-slot self-healing in any service from reopening retired inventory. New console types may generate slots matching the saved windows. If the duration changes, replacement slots overlapping a grandfathered reservation are not offered on that date; unreserved dates use the new grid. After reservations are resolved, saving again or the scheduled inventory extension regenerates the affected grid. PostgreSQL serializes inventory replacement with concurrent inventory writes through a table lock. Cafes without console types can still save their hours for later setup.

Verification commands:

```sh
python -m pytest tests/test_operating_hours.py -q
# Optional: isolated schemas on a local disposable PostgreSQL database
HOURS_TEST_DATABASE_URL=postgresql+psycopg2:///postgres python -m pytest tests/test_operating_hours.py -q
# From hash-dashboard:
node --test tests/operating-hours.test.cjs
```

Tests exercise extracted production handlers against real SQLite and PostgreSQL tables: owner authentication, preserved bookings and QR holds, release and self-healing guards, duplicate templates, new console types, day closure/reopening, far-future inventory, overnight/24-hour hours and input validation. Booking slot-list caches and expected-grid caches are disabled so the next request reads the saved schedule; already-open clients need their normal refresh/refetch. Frontend tests cover normalization and actual save/cancel handlers. A live browser/production deployment is not part of this verification.
