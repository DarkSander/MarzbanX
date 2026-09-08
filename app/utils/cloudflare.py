import requests

CF_API_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareError(Exception):
    pass


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _raise_for_api_error(data: dict):
    if not data.get("success"):
        errors = "; ".join(e.get("message", str(e)) for e in data.get("errors", []))
        raise CloudflareError(errors or "Unknown Cloudflare API error")


def get_zone_id(token: str, domain: str) -> str:
    """Find the Cloudflare zone that owns `domain`, trying progressively
    shorter suffixes (e.g. sub.example.com -> example.com -> com)."""
    parts = domain.strip(".").split(".")
    for i in range(len(parts) - 1):
        candidate = ".".join(parts[i:])
        resp = requests.get(
            f"{CF_API_BASE}/zones",
            headers=_headers(token),
            params={"name": candidate},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        _raise_for_api_error(data)
        if data.get("result"):
            return data["result"][0]["id"]

    raise CloudflareError(f'No Cloudflare zone found that could serve "{domain}"')


def create_txt_record(token: str, zone_id: str, name: str, content: str, ttl: int = 60) -> str:
    resp = requests.post(
        f"{CF_API_BASE}/zones/{zone_id}/dns_records",
        headers=_headers(token),
        json={"type": "TXT", "name": name, "content": content, "ttl": ttl},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _raise_for_api_error(data)
    return data["result"]["id"]


def delete_txt_record(token: str, zone_id: str, record_id: str):
    resp = requests.delete(
        f"{CF_API_BASE}/zones/{zone_id}/dns_records/{record_id}",
        headers=_headers(token),
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _raise_for_api_error(data)
