from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.core.database import Base

class SidebarItem(Base):
    __tablename__ = "sidebar_items"
    
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(255), nullable=False)
    title = Column(String(120), nullable=True)
    caption = Column(Text, nullable=True)
    order = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SidebarItem {self.id} {self.title or ''}>"

    def to_dict(self):
        return {
            "id": self.id,
            "image_url": self.image_url,
            "title": self.title,
            "caption": self.caption,
            "order": self.order,
            "active": self.active,
        }


class HomepageSlide(Base):
    __tablename__ = "homepage_slides"
    
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(255), nullable=False)
    caption = Column(String(255), nullable=True)
    order = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<HomepageSlide {self.id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "image_url": self.image_url,
            "caption": self.caption,
            "order": self.order,
            "active": self.active,
        }


class HomepageAd(Base):
    __tablename__ = "homepage_ads"
    
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String(255), nullable=False)
    title = Column(String(140), nullable=True)
    caption = Column(Text, nullable=True)
    link = Column(String(255), nullable=True)
    order = Column(Integer, default=0, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<HomepageAd {self.id} {self.title or ''}>"

    def to_dict(self):
        return {
            "id": self.id,
            "image_url": self.image_url,
            "title": self.title,
            "caption": self.caption,
            "link": self.link,
            "order": self.order,
            "active": self.active,
        }