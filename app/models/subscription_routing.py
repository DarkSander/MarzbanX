from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SubscriptionRoutingSource(str, Enum):
    roscomvpn_default = "roscomvpn_default"
    roscomvpn_whitelist = "roscomvpn_whitelist"
    custom_link = "custom_link"
    custom_json = "custom_json"


class SubscriptionRoutingModify(BaseModel):
    enabled: bool
    source: SubscriptionRoutingSource
    custom_value: Optional[str] = None
    happ_only: bool = False


class SubscriptionRoutingResponse(BaseModel):
    enabled: bool
    source: SubscriptionRoutingSource
    custom_value: Optional[str] = None
    happ_only: bool
    fetched_at: Optional[datetime] = None
    last_error: Optional[str] = None
    # what subscriptions would carry right now, for the dashboard preview
    link: Optional[str] = None
    link_length: Optional[int] = None
    max_header_size: int
    profile: Optional[dict] = None
