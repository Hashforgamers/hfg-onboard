CREATE INDEX IF NOT EXISTS ix_available_games_game_name_lower
    ON available_games (LOWER(game_name));

CREATE INDEX IF NOT EXISTS ix_available_games_vendor_id
    ON available_games (vendor_id);

CREATE INDEX IF NOT EXISTS ix_available_games_single_slot_price
    ON available_games (single_slot_price);

CREATE INDEX IF NOT EXISTS ix_vendor_games_game_vendor_available
    ON vendor_games (game_id, vendor_id, is_available);

CREATE INDEX IF NOT EXISTS ix_physical_address_pincode_state_active
    ON physical_address (pincode, state, is_active);

CREATE INDEX IF NOT EXISTS ix_images_vendor_id_id
    ON images (vendor_id, id);

CREATE INDEX IF NOT EXISTS ix_console_pricing_offers_active_lookup
    ON console_pricing_offers (available_game_id, is_active, start_date, end_date, offered_price);
