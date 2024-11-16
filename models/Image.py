from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from db.extensions import db
from datetime import datetime

class Image(db.Model):
    __tablename__ = 'images'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False)
    image_id = Column(String(255), nullable=False)  # Google Drive file ID
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    vendor = relationship('Vendor', back_populates='images')
