"""Devices online per subscription, counted from the IPs Xray sees each user
connected from (main core and every node). Only IPs with an open connection
are reported, so a device counts while it is actually in use."""
import ipaddress
import threading
from collections import defaultdict
from datetime import datetime
from typing import Dict, Optional

from config import DEVICE_LIMIT_DEFAULT

# user id -> {device: unix time it was first seen}
Snapshot = Dict[int, Dict[str, int]]

_lock = threading.Lock()
_snapshot: Snapshot = {}
_updated_at: Optional[datetime] = None


def device_key(ip: str) -> str:
    """One device per IPv4 address. IPv6 is counted per /64: phones rotate
    their temporary IPv6 addresses inside the same network."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 6:
        if addr.ipv4_mapped:
            return str(addr.ipv4_mapped)
        return str(ipaddress.ip_network(f"{addr}/64", strict=False))
    return str(addr)


def effective_limit(user_limit: Optional[int]) -> int:
    """The limit that applies to a user; 0 means no limit."""
    return DEVICE_LIMIT_DEFAULT if user_limit is None else user_limit


def collect() -> Snapshot:
    """Ask every running core who is online and from where."""
    from app import xray
    from xray_api import exc as xray_exc

    apis = [xray.api] if xray.core.started else []
    apis += [node.api for node in list(xray.nodes.values()) if node.connected and node.started]

    result: Snapshot = defaultdict(dict)
    for api in apis:
        try:
            emails = api.get_all_online_users(timeout=10)
        except (xray_exc.XrayError, ConnectionError):
            continue
        for email in emails:
            try:
                user_id = int(email.split('.', 1)[0])
            except ValueError:
                continue
            if user_id <= 0:  # the SS-2022 placeholder
                continue
            try:
                ips = api.get_user_online_ips(email, timeout=10)
            except (xray_exc.XrayError, ConnectionError):
                continue
            for ip, first_seen in ips.items():
                key = device_key(ip)
                known = result[user_id].get(key)
                result[user_id][key] = min(known, first_seen) if known else first_seen
    return dict(result)


def store(snapshot: Snapshot):
    global _snapshot, _updated_at
    with _lock:
        _snapshot = snapshot
        _updated_at = datetime.utcnow()


def get(user_id: int):
    """(devices of the user from the last check, when that check ran)."""
    with _lock:
        return dict(_snapshot.get(user_id, {})), _updated_at
