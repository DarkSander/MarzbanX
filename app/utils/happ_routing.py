"""Happ routing profile delivered with subscriptions.

Happ (and INCY) read a `routing` response header holding a deeplink:
`happ://routing/onadd/<base64 JSON>` adds the profile and activates it,
`happ://routing/add/<base64 JSON>` only adds it to the list.
"""
import base64
import json
import re
from datetime import datetime, timedelta
from typing import Optional

import requests

from app import logger
from app.db import GetDB, Session, crud
from app.db.models import SubscriptionRouting
from config import SUB_ROUTING_MAX_HEADER_SIZE

PRESET_URLS = {
    "roscomvpn_default":
        "https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/main/HAPP/DEFAULT.DEEPLINK",
    "roscomvpn_whitelist":
        "https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/main/HAPP/WHITELIST.DEEPLINK",
}
REFRESH_EVERY = timedelta(days=1)
FETCH_TIMEOUT = 10

_DEEPLINK_RE = re.compile(r"^happ://routing/(?:add|onadd)/(\S+)$")
_HAPP_CLIENT_RE = re.compile(r"^(happ|incy)/", re.IGNORECASE)


class RoutingError(ValueError):
    pass


def decode_deeplink(link: str) -> dict:
    """Validates a happ://routing/add|onadd/<base64> link and returns the
    profile it carries."""
    match = _DEEPLINK_RE.match(link.strip())
    if not match:
        raise RoutingError("expected happ://routing/onadd/<base64> or happ://routing/add/<base64>")
    payload = match.group(1).replace("-", "+").replace("_", "/")
    payload += "=" * (-len(payload) % 4)
    try:
        profile = json.loads(base64.b64decode(payload, validate=True))
    except ValueError as e:
        raise RoutingError(f"payload is not base64-encoded JSON: {e}")
    if not isinstance(profile, dict):
        raise RoutingError("profile must be a JSON object")
    return profile


def encode_profile(profile_json: str) -> str:
    """Builds an onadd deeplink from a profile given as JSON text."""
    try:
        profile = json.loads(profile_json)
    except ValueError as e:
        raise RoutingError(f"invalid JSON: {e}")
    if not isinstance(profile, dict):
        raise RoutingError("profile must be a JSON object")
    payload = json.dumps(profile, ensure_ascii=False, separators=(",", ":")).encode()
    return "happ://routing/onadd/" + base64.b64encode(payload).decode()


def validate_custom_value(source: str, value: Optional[str]):
    if source not in ("custom_link", "custom_json"):
        return
    if not value or not value.strip():
        raise RoutingError("a custom link or JSON profile is required for this source")
    if source == "custom_link":
        decode_deeplink(value)
    else:
        encode_profile(value)


def resolve_link(settings: SubscriptionRouting) -> Optional[str]:
    """The deeplink the current settings produce, regardless of `enabled`."""
    if settings.source in PRESET_URLS:
        return settings.cached_link if settings.cached_source == settings.source else None
    if not settings.custom_value:
        return None
    if settings.source == "custom_json":
        return encode_profile(settings.custom_value)
    return settings.custom_value.strip()


def refresh(force: bool = False):
    """Downloads the selected preset if the cached copy is missing, older than
    a day or belongs to another preset. On failure the previously saved copy
    keeps being served."""
    with GetDB() as db:
        settings = crud.get_subscription_routing(db)
        if settings is None or settings.source not in PRESET_URLS:
            return
        if (not force and settings.cached_source == settings.source and settings.fetched_at
                and datetime.utcnow() - settings.fetched_at < REFRESH_EVERY):
            return
        source = settings.source

    try:
        resp = requests.get(PRESET_URLS[source], timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        link = resp.text.strip()
        decode_deeplink(link)
    except (requests.RequestException, RoutingError) as e:
        logger.warning(f'Failed to refresh Happ routing preset "{source}": {e}')
        with GetDB() as db:
            settings = crud.get_subscription_routing(db)
            settings.last_error = str(e)[:1024]
            db.commit()
        return

    with GetDB() as db:
        settings = crud.get_subscription_routing(db)
        settings.cached_source = source
        settings.cached_link = link
        settings.fetched_at = datetime.utcnow()
        settings.last_error = None
        db.commit()


def routing_header(db: Session, user_agent: str) -> Optional[str]:
    """Value for the subscription's `routing` header, or None to omit it."""
    settings = crud.get_subscription_routing(db)
    if settings is None or not settings.enabled:
        return None
    if settings.happ_only and not _HAPP_CLIENT_RE.match(user_agent):
        return None

    link = resolve_link(settings)
    if link and len(link) > SUB_ROUTING_MAX_HEADER_SIZE:
        logger.warning(
            f"Happ routing profile is {len(link)} bytes, over SUB_ROUTING_MAX_HEADER_SIZE="
            f"{SUB_ROUTING_MAX_HEADER_SIZE}; not sending it"
        )
        return None
    return link
