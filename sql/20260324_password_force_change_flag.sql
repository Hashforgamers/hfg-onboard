-- Ensure temporary password flow can force password update on first login.
ALTER TABLE password_manager
ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT FALSE;
