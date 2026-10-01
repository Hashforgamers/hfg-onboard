CREATE TABLE IF NOT EXISTS cafe_requests (
 id BIGSERIAL PRIMARY KEY,
 vendor_id INTEGER NOT NULL REFERENCES vendors(id),
 document_id INTEGER REFERENCES documents(id),
 kind VARCHAR(30) NOT NULL CHECK (kind IN ('document_reupload','support_issue')),
 message TEXT NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'open',
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS cafe_requests_vendor_idx ON cafe_requests(vendor_id, created_at DESC);
