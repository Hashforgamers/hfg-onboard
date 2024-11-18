from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from db.extensions import db
from models.vendor import Vendor

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

    # Polymorphic fields
    parent_id = Column(Integer, nullable=False)
    parent_type = Column(String(50), nullable=False)

    # Relationships
    vendor = relationship("Vendor", back_populates="physical_address", foreign_keys=[parent_id])

    __mapper_args__ = {
        'polymorphic_identity': 'physical_address',
        'polymorphic_on': parent_type
    }