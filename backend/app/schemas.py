from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class HealthResponse(BaseModel):
    status: str


class InvestorCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=255)


class InvestorRead(BaseModel):
    id: UUID
    email: EmailStr
    name: str
    voice_guide: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StartupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    founder_email: EmailStr | None = None
    status: str = Field(default="watching", min_length=1, max_length=64)


class StartupRead(BaseModel):
    id: UUID
    name: str
    domain: str | None
    founder_email: EmailStr | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InteractionCreate(BaseModel):
    startup_id: UUID
    source: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1)


class InteractionRead(BaseModel):
    id: UUID
    startup_id: UUID
    source: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
