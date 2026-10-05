import re
from urllib.parse import urlsplit, parse_qs, urlencode
from sqlalchemy import text
from db.extensions import db


def validate_release(data):
    version = str(data.get('version') or '').strip()
    source = str(data.get('source_url') or '').strip()
    download = str(data.get('download_url') or '').strip()
    notes = str(data.get('notes') or '').strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,79}', version):
        raise ValueError('Enter a version using letters, numbers, dots or hyphens.')
    if source:
        parsed=urlsplit(source)
        if parsed.scheme!='https' or parsed.netloc!='github.com' or parsed.query or parsed.fragment:
            raise ValueError('Source link must be an HTTPS github.com link without query parameters.')
    if download:
        parsed=urlsplit(download)
        if parsed.scheme!='https' or parsed.fragment or parsed.username or parsed.password:
            raise ValueError('Use a secure Google Drive file link or GitHub Release installer link.')
        if parsed.netloc=='github.com':
            if parsed.query or not re.fullmatch(r'/[^/]+/[^/]+/releases/download/[^/]+/[^/]+\.(exe|msi|zip)',parsed.path,re.I):
                raise ValueError('GitHub download must be a Release .exe, .msi or .zip asset; source-code archives are not installers.')
        elif parsed.netloc=='drive.google.com':
            params=parse_qs(parsed.query)
            match=re.fullmatch(r'/file/d/([A-Za-z0-9_-]+)/view/?',parsed.path)
            file_id=match.group(1) if match else (params.get('id',[''])[0] if parsed.path in ('/open','/uc') else '')
            if not re.fullmatch(r'[A-Za-z0-9_-]+',file_id):
                raise ValueError('Paste the Google Drive share link for one installer file, not a folder.')
            if set(params)-{'id','export','usp','resourcekey','authuser'}:
                raise ValueError('Google Drive link has unsupported parameters.')
            resource=params.get('resourcekey',[''])[0]
            if resource and not re.fullmatch(r'[A-Za-z0-9_-]+',resource):
                raise ValueError('Invalid Google Drive resource key.')
            download=f'https://drive.google.com/file/d/{file_id}/view'
            if resource: download+='?'+urlencode({'resourcekey':resource})
        else:
            raise ValueError('Use a Google Drive file share link or GitHub Release installer link.')
    if len(notes) > 10000: raise ValueError('Release notes must be under 10,000 characters.')
    return dict(version=version, source_url=source, download_url=download, notes=notes)


def list_releases():
    return [dict(row) for row in db.session.execute(text('SELECT id,version,source_url,download_url,notes,active,created_at::text FROM kiosk_releases ORDER BY id DESC')).mappings()]
