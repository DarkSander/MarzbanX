from datetime import datetime, timedelta

from app import logger, scheduler
from app.db import GetDB, crud
from app.utils.acme import AcmeError, issue_and_store_certificate
from app.utils.cloudflare import CloudflareError
from config import ACME_RENEWAL_THRESHOLD_DAYS, JOB_CERTIFICATE_RENEWAL_INTERVAL


def renew_expiring_certificates():
    threshold = datetime.utcnow() + timedelta(days=ACME_RENEWAL_THRESHOLD_DAYS)

    with GetDB() as db:
        due = [
            (cert.domain, cert.inbound_tags or [], cert.auto_renew)
            for cert in crud.get_certificates(db)
            if cert.auto_renew and cert.status != "pending"
            and (cert.expires_at is None or cert.expires_at <= threshold)
        ]

    for domain, inbound_tags, auto_renew in due:
        logger.info(f'Auto-renewing certificate for "{domain}"')
        try:
            issue_and_store_certificate(domain, inbound_tags, auto_renew)
        except (AcmeError, CloudflareError) as e:
            logger.error(f'Auto-renewal failed for "{domain}": {e}')


scheduler.add_job(
    renew_expiring_certificates, 'interval', coalesce=True,
    seconds=JOB_CERTIFICATE_RENEWAL_INTERVAL, max_instances=1,
)
