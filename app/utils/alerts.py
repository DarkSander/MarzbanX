"""Alerts to admins about the panel itself, sent to Telegram and Discord:
the Xray core going down or coming back, certificates that failed to renew,
subscriptions used by more devices than allowed."""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from telebot.formatting import escape_html

from app import logger
from app.utils.concurrency import threaded_function
from config import NOTIFY_DEVICE_LIMIT, NOTIFY_SYSTEM_ALERTS

RED = int("f56565", 16)
GREEN = int("68d391", 16)
ORANGE = int("f6ad55", 16)

Fields = List[Tuple[str, str]]


@threaded_function
def _send(title: str, fields: Fields, color: int, footer: str = ""):
    # imported here: both modules import the app, which imports the jobs
    from app import telegram
    from app.discord.handlers.report import send_webhooks

    lines = [f"<b>{escape_html(title)}</b>", "➖➖➖➖➖➖➖➖➖"]
    lines += [f"<b>{escape_html(k)}:</b> {escape_html(v)}" if k else escape_html(v) for k, v in fields]
    if footer:
        lines += ["", f"<pre>{escape_html(footer)}</pre>"]
    try:
        telegram.report(text="\n".join(lines))
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")

    description = "\n".join(f"**{k}:** {v}" if k else v for k, v in fields)
    if footer:
        description += f"\n```\n{footer[-1500:]}\n```"
    try:
        send_webhooks({"content": "", "embeds": [{"title": title, "description": description, "color": color}]})
    except Exception as e:
        logger.error(f"Discord alert failed: {e}")


def _duration(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 3600:
        return f"{seconds // 60} min"
    return f"{seconds // 3600} h {seconds % 3600 // 60} min"


def core_down(where: str, log_tail: List[str]):
    if NOTIFY_SYSTEM_ALERTS:
        _send(f"🔴 Xray core is down ({where})",
              [("", "The core stopped unexpectedly, restarting it.")],
              RED, footer="\n".join(log_tail[-15:]))


def core_restored(where: str, down_for: timedelta):
    if NOTIFY_SYSTEM_ALERTS:
        _send(f"🟢 Xray core is running again ({where})",
              [("Was down for", _duration(down_for))], GREEN)


def certificate_renewal_failed(domain: str, error: str, expires_at: Optional[datetime]):
    if not NOTIFY_SYSTEM_ALERTS:
        return
    fields = [("Domain", domain), ("Error", error[:500])]
    if expires_at:
        left = expires_at - datetime.utcnow()
        fields.append(("Expires", f"{expires_at:%Y-%m-%d %H:%M} UTC "
                                  f"({'already expired' if left.total_seconds() <= 0 else f'in {left.days} days'})"))
    fields.append(("", "Auto-renewal will retry on the next run."))
    _send("⚠️ Certificate renewal failed", fields, ORANGE)


def device_limit_exceeded(username: str, devices: List[str], limit: int):
    if NOTIFY_DEVICE_LIMIT:
        _send("📱 Device limit exceeded",
              [("User", username), ("Devices online", f"{len(devices)} (limit {limit})"),
               ("IPs", ", ".join(devices))],
              ORANGE)
