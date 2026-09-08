import json
import time
from datetime import datetime, timedelta

import josepy as jose
import requests
from acme import challenges, client, crypto_util, errors, messages
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app import logger
from app.db import GetDB, crud
from app.utils.cloudflare import CloudflareError, create_txt_record, delete_txt_record, get_zone_id
from config import ACME_DIRECTORY_URL, ACME_EMAIL, CLOUDFLARE_API_TOKEN

USER_AGENT = "MarzbanX-ACME/1.0"
ACCOUNT_KEY_SIZE = 2048
CERT_KEY_SIZE = 2048
DNS_PROPAGATION_TIMEOUT = 180
DNS_PROPAGATION_POLL_INTERVAL = 5
DOH_RESOLVERS = (
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/resolve",
)


class AcmeError(Exception):
    pass


def get_effective_acme_settings() -> dict:
    """Resolves the email/Cloudflare token/directory URL to actually use:
    the admin-configured values from the database take priority, falling
    back to the ACME_EMAIL/CLOUDFLARE_API_TOKEN/ACME_DIRECTORY_URL env vars
    for anything left unset in the database."""
    with GetDB() as db:
        settings = crud.get_acme_settings(db)

    return {
        "email": (settings.email if settings else None) or ACME_EMAIL,
        "cloudflare_api_token": (settings.cloudflare_api_token if settings else None) or CLOUDFLARE_API_TOKEN,
        "directory_url": (settings.directory_url if settings else None) or ACME_DIRECTORY_URL,
    }


def _generate_rsa_key_pem(key_size: int) -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _get_acme_client(email: str, directory_url: str) -> client.ClientV2:
    with GetDB() as db:
        account = crud.get_acme_account(db)
        if account is None:
            account_key_pem = _generate_rsa_key_pem(ACCOUNT_KEY_SIZE)
        else:
            account_key_pem = account.private_key.encode()

    jwk = jose.JWKRSA(key=jose.ComparableRSAKey(
        serialization.load_pem_private_key(account_key_pem, password=None)
    ))
    net = client.ClientNetwork(jwk, user_agent=USER_AGENT)
    directory = client.ClientV2.get_directory(directory_url, net)
    acme_client = client.ClientV2(directory, net)

    try:
        # First time this account key is used: register a fresh account.
        regr = acme_client.new_account(
            messages.NewRegistration.from_data(email=email, terms_of_service_agreed=True)
        )
    except errors.ConflictError as e:
        # The ACME server already has an account for this key (e.g. every
        # call after the first one) -- new_account() treats the resulting
        # HTTP 200 as a conflict instead of returning the resource, so look
        # the existing account up instead using the location it reports.
        regr = acme_client.query_registration(
            messages.RegistrationResource(uri=e.location, body=messages.Registration())
        )

    with GetDB() as db:
        account = crud.get_acme_account(db)
        if account is None:
            crud.create_acme_account(db, email=email, private_key=account_key_pem.decode(),
                                     account_url=regr.uri)

    return acme_client


def _wait_for_dns_propagation(record_name: str, expected_value: str):
    deadline = time.time() + DNS_PROPAGATION_TIMEOUT
    quoted_expected = f'"{expected_value}"'

    while time.time() < deadline:
        for resolver in DOH_RESOLVERS:
            try:
                resp = requests.get(
                    resolver,
                    params={"name": record_name, "type": "TXT"},
                    headers={"Accept": "application/dns-json"},
                    timeout=10,
                )
                resp.raise_for_status()
                answers = resp.json().get("Answer", [])
                if any(a.get("data") == quoted_expected for a in answers):
                    return
            except (requests.RequestException, ValueError):
                continue

        time.sleep(DNS_PROPAGATION_POLL_INTERVAL)

    raise AcmeError(
        f'Timed out waiting for TXT record "{record_name}" to propagate publicly'
    )


def issue_certificate(domain: str) -> dict:
    """Runs the full ACME DNS-01 (Cloudflare) issuance flow for `domain` and
    returns {"certificate": fullchain_pem, "private_key": key_pem,
    "issued_at": dt, "expires_at": dt}. Raises AcmeError/CloudflareError on
    failure; the TXT record is always cleaned up before returning/raising.
    """
    settings = get_effective_acme_settings()
    if not settings["email"]:
        raise AcmeError("No ACME email configured (set it in the Certificates panel or ACME_EMAIL)")
    if not settings["cloudflare_api_token"]:
        raise AcmeError("No Cloudflare API token configured (set it in the Certificates panel or CLOUDFLARE_API_TOKEN)")
    cf_token = settings["cloudflare_api_token"]

    acme_client = _get_acme_client(settings["email"], settings["directory_url"])

    zone_id = get_zone_id(cf_token, domain)

    cert_key_pem = _generate_rsa_key_pem(CERT_KEY_SIZE)
    csr_pem = crypto_util.make_csr(cert_key_pem, [domain])

    orderr = acme_client.new_order(csr_pem)

    record_id = None
    record_name = None
    try:
        for authz in orderr.authorizations:
            dns_challenge = next(
                (c for c in authz.body.challenges if isinstance(c.chall, challenges.DNS01)),
                None,
            )
            if dns_challenge is None:
                raise AcmeError(f'No DNS-01 challenge offered for "{domain}"')

            validation_value = dns_challenge.chall.validation(acme_client.net.key)
            record_name = dns_challenge.chall.validation_domain_name(domain)

            record_id = create_txt_record(cf_token, zone_id, record_name, validation_value)
            _wait_for_dns_propagation(record_name, validation_value)

            response = dns_challenge.response(acme_client.net.key)
            acme_client.answer_challenge(dns_challenge, response)

        finalized = acme_client.poll_and_finalize(
            orderr, deadline=datetime.utcnow() + timedelta(seconds=90)
        )
    except errors.Error as e:
        raise AcmeError(f'ACME issuance failed for "{domain}": {e}')
    finally:
        if record_id:
            try:
                delete_txt_record(cf_token, zone_id, record_id)
            except CloudflareError as e:
                logger.warning(f'Failed to clean up ACME TXT record for "{domain}": {e}')

    fullchain_pem = finalized.fullchain_pem
    cert = x509.load_pem_x509_certificate(fullchain_pem.encode())

    return {
        "certificate": fullchain_pem,
        "private_key": cert_key_pem.decode(),
        "issued_at": datetime.utcnow(),
        "expires_at": cert.not_valid_after,
    }


def apply_certificate_to_xray(domain: str, certificate_pem: str, private_key_pem: str, inbound_tags: list):
    """Writes the given certificate/key into the streamSettings.tlsSettings
    of the selected inbounds in the persisted core config, then restarts
    the core (and connected nodes) so the change takes effect."""
    from app import xray
    from app.xray.config import XRayConfig
    from config import XRAY_JSON

    with open(XRAY_JSON, "r") as f:
        raw_config = json.loads(f.read())

    cert_lines = certificate_pem.strip().splitlines()
    key_lines = private_key_pem.strip().splitlines()

    changed = False
    for inbound in raw_config.get("inbounds", []):
        if inbound.get("tag") not in inbound_tags:
            continue

        tls_settings = (
            inbound.setdefault("streamSettings", {}).setdefault("tlsSettings", {})
        )
        tls_settings["certificates"] = [{
            "certificate": cert_lines,
            "key": key_lines,
        }]
        changed = True

    if not changed:
        return

    config = XRayConfig(raw_config, api_port=xray.config.api_port)
    xray.config = config
    with open(XRAY_JSON, "w") as f:
        f.write(json.dumps(raw_config, indent=4))

    startup_config = xray.config.include_db_users()
    xray.core.restart(startup_config)
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)

    xray.hosts.update()


def issue_and_store_certificate(domain: str, inbound_tags: list, auto_renew: bool) -> "Certificate":
    """High-level entry point used by the router and the renewal job:
    issues the certificate, persists it, and (if requested) applies it to
    the selected Xray inbounds. Persists failure status/message on error
    instead of raising, so callers running in the background can just log.
    """
    with GetDB() as db:
        cert = crud.upsert_certificate(db, domain, inbound_tags, auto_renew)
        cert_id = cert.id

    try:
        result = issue_certificate(domain)
    except (AcmeError, CloudflareError) as e:
        with GetDB() as db:
            cert = crud.get_certificate_by_id(db, cert_id)
            cert.status = "error"
            cert.last_error = str(e)
            db.commit()
        logger.error(f'Certificate issuance failed for "{domain}": {e}')
        raise

    with GetDB() as db:
        cert = crud.get_certificate_by_id(db, cert_id)
        cert.certificate = result["certificate"]
        cert.private_key = result["private_key"]
        cert.issued_at = result["issued_at"]
        cert.expires_at = result["expires_at"]
        cert.status = "issued"
        cert.last_error = None
        db.commit()
        db.refresh(cert)
        domain_, cert_pem, key_pem, tags = cert.domain, cert.certificate, cert.private_key, cert.inbound_tags

    if tags:
        apply_certificate_to_xray(domain_, cert_pem, key_pem, tags)

    logger.info(f'Certificate issued for "{domain}", expires {result["expires_at"]}')
    return cert
