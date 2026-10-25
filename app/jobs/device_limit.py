from datetime import datetime, timedelta

from app import logger, scheduler
from app.db import GetDB
from app.db.models import User
from app.utils import alerts, devices
from config import DEVICE_LIMIT_NOTIFY_INTERVAL_MINUTES, JOB_DEVICE_LIMIT_INTERVAL

# user id -> when admins were last told about it
_notified_at = {}


def check_device_limits():
    snapshot = devices.collect()
    devices.store(snapshot)
    if not snapshot:
        return

    with GetDB() as db:
        rows = db.query(User.id, User.username, User.device_limit) \
            .filter(User.id.in_(list(snapshot))).all()

    now = datetime.utcnow()
    repeat_after = timedelta(minutes=DEVICE_LIMIT_NOTIFY_INTERVAL_MINUTES)
    for user_id, username, user_limit in rows:
        limit = devices.effective_limit(user_limit)
        online = snapshot.get(user_id, {})
        if limit <= 0 or len(online) <= limit:
            continue

        last = _notified_at.get(user_id)
        if last and now - last < repeat_after:
            continue
        _notified_at[user_id] = now
        logger.warning(f'User "{username}" is online from {len(online)} devices (limit {limit})')
        # oldest first: the newest ones are the likely extra devices
        alerts.device_limit_exceeded(username, sorted(online, key=online.get), limit)


scheduler.add_job(check_device_limits, 'interval', seconds=JOB_DEVICE_LIMIT_INTERVAL,
                  coalesce=True, max_instances=1)
