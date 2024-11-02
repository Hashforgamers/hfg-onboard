from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from db.extensions import db

class PhysicalAddress(db.Model):
    __tablename__ = 'physical_address'
    
    id = Column(Integer, primary_key=True)
    address_type = Column(String(50), nullable=False)
    addressLine1 = Column(String(255), nullable=False)  # Updated this line
    addressLine2 = Column(String(255))
    pincode = Column(String(10), nullable=False)
    state = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    latitude = Column(String(20))
    longitude = Column(String(20))

    vendors = relationship('Vendor', back_populates='physical_address')
