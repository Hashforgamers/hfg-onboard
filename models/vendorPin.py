from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from db.extensions import db

class VendorPin(db.Model):
    __tablename__ = 'vendor_pins'

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendor.id'), nullable=False)
    pin_code = Column(String(6), unique=True, nullable=False)

    vendor = relationship('Vendor', back_populates='pin')

    def __repr__(self):
        return f"<VendorPin(vendor_id={self.vendor_id}, pin_code='{self.pin_code}')>"
