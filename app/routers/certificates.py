from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app import logger, xray
from app.db import Session, crud, get_db
from app.db.models import Certificate as DBCertificate
from app.models.admin import Admin
from app.models.certificate import (
    AcmeSettingsRequest,
    AcmeSettingsResponse,
    CertificateRequest,
    CertificateResponse,
)
from app.utils import responses
from app.utils.acme import AcmeError, issue_and_store_certificate, panel_cert_paths
from app.utils.cloudflare import CloudflareError
from config import ACME_DIRECTORY_URL, ACME_EMAIL, CLOUDFLARE_API_TOKEN

router = APIRouter(
    tags=["Certificate"], prefix="/api", responses={401: responses._401, 403: responses._403}
)


def _to_response(cert: DBCertificate) -> CertificateResponse:
    days_remaining = None
    if cert.expires_at:
        days_remaining = (cert.expires_at - datetime.utcnow()).days

    panel_cert_file = panel_key_file = None
    if cert.apply_to_panel:
        panel_cert_file, panel_key_file = panel_cert_paths(cert.domain)

    return CertificateResponse(
        id=cert.id,
        domain=cert.domain,
        inbound_tags=cert.inbound_tags or [],
        auto_renew=cert.auto_renew,
        apply_to_panel=cert.apply_to_panel,
        status=cert.status,
        last_error=cert.last_error,
        issued_at=cert.issued_at,
        expires_at=cert.expires_at,
        days_remaining=days_remaining,
        panel_cert_file=panel_cert_file,
        panel_key_file=panel_key_file,
    )


def _run_issuance(domain: str, inbound_tags: List[str], auto_renew: bool, apply_to_panel: bool):
    try:
        issue_and_store_certificate(domain, inbound_tags, auto_renew, apply_to_panel)
    except (AcmeError, CloudflareError):
        pass  # already logged and persisted by issue_and_store_certificate


@router.get("/certificates/settings", response_model=AcmeSettingsResponse)
def get_acme_settings(db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)):
    """Retrieve the configured ACME email / directory URL, and whether a
    Cloudflare API token is set (its value is never returned)."""
    settings = crud.get_acme_settings(db)

    return AcmeSettingsResponse(
        email=(settings.email if settings else None) or ACME_EMAIL or None,
        cloudflare_api_token_configured=bool(
            (settings.cloudflare_api_token if settings else None) or CLOUDFLARE_API_TOKEN
        ),
        directory_url=(settings.directory_url if settings else None) or ACME_DIRECTORY_URL,
    )


@router.put("/certificates/settings", response_model=AcmeSettingsResponse)
def update_acme_settings(
    payload: AcmeSettingsRequest,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Update the ACME email / Cloudflare API token / directory URL used
    for certificate issuance. Leave cloudflare_api_token empty to keep the
    currently stored token unchanged."""
    settings = crud.save_acme_settings(
        db, payload.email, payload.cloudflare_api_token, payload.directory_url
    )
    return AcmeSettingsResponse(
        email=settings.email,
        cloudflare_api_token_configured=bool(settings.cloudflare_api_token),
        directory_url=settings.directory_url or ACME_DIRECTORY_URL,
    )


@router.get("/certificates", response_model=List[CertificateResponse])
def get_certificates(db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)):
    """List all Let's Encrypt certificates managed by the panel."""
    return [_to_response(c) for c in crud.get_certificates(db)]


@router.post("/certificates", response_model=CertificateResponse)
def request_certificate(
    payload: CertificateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Request (or re-request) a Let's Encrypt certificate for a domain.
    Issuance runs in the background; poll GET /certificates for status."""
    for tag in payload.inbound_tags:
        if tag not in xray.config.inbounds_by_tag:
            raise HTTPException(status_code=400, detail=f'Inbound "{tag}" does not exist')

    cert = crud.upsert_certificate(
        db, payload.domain, payload.inbound_tags, payload.auto_renew, payload.apply_to_panel
    )
    background_tasks.add_task(
        _run_issuance, payload.domain, payload.inbound_tags, payload.auto_renew, payload.apply_to_panel
    )
    return _to_response(cert)


@router.post("/certificates/{cert_id}/reissue", response_model=CertificateResponse)
def reissue_certificate(
    cert_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Manually trigger reissuance/renewal of an existing certificate."""
    cert = crud.get_certificate_by_id(db, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    cert.status = "pending"
    db.commit()
    db.refresh(cert)

    background_tasks.add_task(
        _run_issuance, cert.domain, cert.inbound_tags or [], cert.auto_renew, cert.apply_to_panel
    )
    return _to_response(cert)


@router.delete("/certificates/{cert_id}", responses={404: responses._404})
def remove_certificate(
    cert_id: int, db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Stop managing a certificate. This does not remove it from any Xray
    inbound it was already applied to."""
    cert = crud.get_certificate_by_id(db, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    crud.delete_certificate(db, cert)
    return {}
