from sqlalchemy import Column, String, DateTime, func
from app.database import Base


class Link(Base):
    __tablename__ = "links"

    short_code = Column(String, primary_key=True, index=True)
    original_url = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LinkAnalytics:
    def __init__(self):
        self.stats = {}