"""Fire-and-forget ping to the website's IndexNow endpoint.

When a cafe goes live or its public details change, the website is told so it
can ask search engines to recrawl the cafe page right away.

    SEO_PING_URL     default https://www.hashforgamers.com/api/seo/indexnow
    SEO_PING_SECRET  shared bearer secret; when unset, pinging is disabled

Never raises and never blocks the caller: the request runs in a daemon thread
with a short timeout, and every failure is only logged.
"""
import logging
import os
import threading

import requests

logger = logging.getLogger(__name__)

DEFAULT_SEO_PING_URL = "https://www.hashforgamers.com/api/seo/indexnow"
TIMEOUT_SECONDS = 5

_disabled_logged = False


def _normalize_ids(vendor_ids):
    if vendor_ids is None:
        return []
    if isinstance(vendor_ids, (int, str)):
        vendor_ids = [vendor_ids]
    seen = []
    for raw in vendor_ids:
        try:
            value = int(raw)
        except (TypeError, ValueError):
            continue
        if value > 0 and value not in seen:
            seen.append(value)
    return seen


def _post(url, secret, payload):
    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            logger.warning("SEO ping returned HTTP %s for %s", response.status_code, payload)
        else:
            logger.info("SEO ping sent for %s", payload)
    except Exception as exc:  # never let a ping failure escape the thread
        logger.warning("SEO ping failed for %s: %s", payload, exc)


def ping_vendors(vendor_ids):
    """Tell the website these cafes changed. Returns the started thread, or None."""
    global _disabled_logged
    try:
        secret = (os.getenv("SEO_PING_SECRET") or "").strip()
        if not secret:
            if not _disabled_logged:
                logger.info("SEO_PING_SECRET not set; SEO pings are disabled")
                _disabled_logged = True
            return None

        ids = _normalize_ids(vendor_ids)
        # An empty list would make the endpoint resubmit every page, so skip it.
        if not ids:
            return None

        url = (os.getenv("SEO_PING_URL") or "").strip() or DEFAULT_SEO_PING_URL
        thread = threading.Thread(
            target=_post, args=(url, secret, {"vendorIds": ids}), name="seo-ping", daemon=True
        )
        thread.start()
        return thread
    except Exception as exc:
        logger.warning("SEO ping could not be scheduled: %s", exc)
        return None
