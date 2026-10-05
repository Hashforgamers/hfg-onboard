from sqlalchemy import Column, Integer, Time
from sqlalchemy.orm import relationship
from db.extensions import db

class Timing(db.Model):
    __tablename__ = 'timing'

    id = Column(Integer, primary_key=True)
    opening_time = Column(Time, nullable=False)
    closing_time = Column(Time, nullable=False)

    # Relationships
    vendors = relationship('Vendor', back_populates='timing', cascade="all, delete-orphan")
