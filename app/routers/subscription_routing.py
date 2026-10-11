from fastapi import APIRouter, Depends, HTTPException

from app.db import Session, crud, get_db
from app.db.models import SubscriptionRouting
from app.models.admin import Admin
from app.models.subscription_routing import (
    SubscriptionRoutingModify,
    SubscriptionRoutingResponse,
)
from app.utils import happ_routing, responses
from config import SUB_ROUTING_MAX_HEADER_SIZE

router = APIRouter(
    tags=["Subscription Routing"], prefix="/api", responses={401: responses._401, 403: responses._403}
)


def _to_response(settings: SubscriptionRouting) -> SubscriptionRoutingResponse:
    link = happ_routing.resolve_link(settings)
    return SubscriptionRoutingResponse(
        enabled=settings.enabled,
        source=settings.source,
        custom_value=settings.custom_value,
        happ_only=settings.happ_only,
        fetched_at=settings.fetched_at if settings.cached_source == settings.source else None,
        last_error=settings.last_error if settings.source in happ_routing.PRESET_URLS else None,
        link=link,
        link_length=len(link) if link else None,
        max_header_size=SUB_ROUTING_MAX_HEADER_SIZE,
        profile=happ_routing.decode_deeplink(link) if link else None,
    )


@router.get("/subscription-routing", response_model=SubscriptionRoutingResponse)
def get_subscription_routing(db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)):
    """Get the Happ routing profile settings sent with subscriptions."""
    return _to_response(crud.get_or_create_subscription_routing(db))


@router.put("/subscription-routing", response_model=SubscriptionRoutingResponse)
def modify_subscription_routing(
    payload: SubscriptionRoutingModify,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Update the Happ routing profile settings. Selecting a preset downloads
    it right away if there's no fresh copy of it yet."""
    try:
        happ_routing.validate_custom_value(payload.source.value, payload.custom_value)
    except happ_routing.RoutingError as e:
        raise HTTPException(status_code=400, detail=str(e))

    settings = crud.get_or_create_subscription_routing(db)
    settings.enabled = payload.enabled
    settings.source = payload.source.value
    settings.happ_only = payload.happ_only
    if payload.custom_value is not None:
        settings.custom_value = payload.custom_value.strip() or None
    db.commit()

    happ_routing.refresh()
    db.refresh(settings)
    return _to_response(settings)


@router.post("/subscription-routing/refresh", response_model=SubscriptionRoutingResponse)
def refresh_subscription_routing(db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)):
    """Re-download the selected preset now."""
    settings = crud.get_or_create_subscription_routing(db)
    if settings.source not in happ_routing.PRESET_URLS:
        raise HTTPException(status_code=400, detail="Only presets can be refreshed")

    happ_routing.refresh(force=True)
    db.refresh(settings)
    return _to_response(settings)
