from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship
from db.extensions import db
from datetime import datetime

class Game(db.Model):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    release_date = Column(Date, nullable=True)
    developer = Column(String(255), nullable=True)
    publisher = Column(String(255), nullable=True)
    genre = Column(String(100), nullable=True)
    cover_image_url = Column(String(255), nullable=True)
    screenshots = Column(JSON, nullable=True)  # List of image URLs
    average_rating = Column(Float, default=0.0)
    trailer_url = Column(String(255), nullable=True)
    multiplayer = Column(Boolean, default=False)
    esrb_rating = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supported_by = relationship('SupportedGame', back_populates='game', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "developer": self.developer,
            "publisher": self.publisher,
            "genre": self.genre,
            "cover_image_url": self.cover_image_url,
            "screenshots": self.screenshots,
            "average_rating": self.average_rating,
            "trailer_url": self.trailer_url,
            "multiplayer": self.multiplayer,
            "esrb_rating": self.esrb_rating,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
