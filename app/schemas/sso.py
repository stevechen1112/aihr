"""Schemas for SSO configuration and OAuth callback."""
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

# ─── Tenant SSO Config ───

class SSOConfigBase(BaseModel):
    provider: str  # "google" | "microsoft"
    client_id: str
    enabled: bool = True
    allowed_domains: List[str] = Field(default_factory=list)
    auto_create_user: bool = True
    default_role: str = "employee"


class SSOConfigCreate(SSOConfigBase):
    client_secret: str


class SSOConfigUpdate(BaseModel):
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    enabled: Optional[bool] = None
    allowed_domains: Optional[List[str]] = None
    auto_create_user: Optional[bool] = None
    default_role: Optional[str] = None


class SSOConfigRead(SSOConfigBase):
    id: UUID
    tenant_id: UUID

    class Config:
        from_attributes = True


class SSOConfigPublic(BaseModel):
    """Safe projection — no secrets exposed to frontend."""
    provider: str
    enabled: bool

    class Config:
        from_attributes = True


# ─── OAuth callback ───

class OAuthCallbackRequest(BaseModel):
    """Frontend sends the authorization code + redirect_uri."""
    code: str
    redirect_uri: str
    tenant_id: UUID
    provider: str  # "google" | "microsoft"
    state: str
    code_verifier: str


class SSOStateRequest(BaseModel):
    tenant_id: UUID
    provider: str


class SSOStateResponse(BaseModel):
    state: str
