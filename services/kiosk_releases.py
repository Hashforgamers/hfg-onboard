import re
from urllib.parse import urlsplit
from sqlalchemy import text
from db.extensions import db


def validate_release(data):
    version = str(data.get('version') or '').strip()
    source = str(data.get('source_url') or '').strip()
    download = str(data.get('download_url') or '').strip()
    notes = str(data.get('notes') or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,79}', version):
        raise ValueError('Enter a version using letters, numbers, dots or hyphens.')
    for value in (source, download):
        if not value: continue
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or parsed.netloc != 'github.com' or parsed.query or parsed.fragment:
            raise ValueError('Use an HTTPS github.com link without query parameters.')
    if not source: raise ValueError('GitHub source link is required.')
    if download and not re.fullmatch(r'/[^/]+/[^/]+/releases/download/[^/]+/[^/]+\.(exe|msi|zip)', urlsplit(download).path, re.I):
        raise ValueError('Download link must point to a GitHub Release .exe, .msi or .zip asset.')
    if len(notes) > 10000: raise ValueError('Release notes must be under 10,000 characters.')
    return dict(version=version, source_url=source, download_url=download, notes=notes)


def list_releases():
    return [dict(row) for row in db.session.execute(text('SELECT id,version,source_url,download_url,notes,active,created_at::text FROM kiosk_releases ORDER BY id DESC')).mappings()]
