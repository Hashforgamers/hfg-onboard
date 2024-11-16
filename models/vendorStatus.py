# models/vendorStatus.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.extensions import db
from datetime import datetime


class VendorStatus(db.Model):
    __tablename__ = 'vendor_statuses'
    
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False)
    status = Column(String, nullable=False)  # e.g., 'active', 'inactive', 'pending_verification'
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Link to Vendor model
    vendor = relationship('Vendor', back_populates='statuses')

    def __str__(self):
        return f"VendorCredential(id={self.id}, vendor_id='{self.vendor_id}', status={self.status}, updated_at='{self.updated_at}')"

    def __repr__(self):
        return self.__str__()    