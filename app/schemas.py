from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None


class LinkResponse(BaseModel):
    short_code: str
    original_url: HttpUrl
    created_at: datetime


class LinkUpdate(BaseModel):
    original_url: HttpUrl


class LinkStatsResponse(BaseModel):
    original_url: str
    created_at: datetime
    clicks: int
    last_used: Optional[datetime] = None