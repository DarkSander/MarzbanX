from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CertificateRequest(BaseModel):
    domain: str
    inbound_tags: List[str] = Field(default_factory=list)
    auto_renew: bool = True


class CertificateResponse(BaseModel):
    id: int
    domain: str
    inbound_tags: List[str]
    auto_renew: bool
    status: str
    last_error: Optional[str] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    days_remaining: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
