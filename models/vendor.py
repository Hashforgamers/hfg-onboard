from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from db.extensions import db
from models.amenity import Amenity
from models.documentSubmitted import DocumentSubmitted
from models.openingDay import OpeningDay
from models.availableGame import AvailableGame
from models.vendorCredentials import VendorCredential
from models.vendorStatus import VendorStatus
from datetime import datetime

class Vendor(db.Model):
    __tablename__ = 'vendors'
    
    id = Column(Integer, primary_key=True)
    cafe_name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)

    # Relationships
    physical_address = relationship(
        'PhysicalAddress',
        primaryjoin="and_(PhysicalAddress.parent_id==Vendor.id, "
                    "PhysicalAddress.parent_type=='vendor')",
        uselist=False,
        cascade="all, delete-orphan"
    )
    contact_info = relationship(
        'ContactInfo',
        primaryjoin="and_(ContactInfo.parent_id==Vendor.id, "
                    "ContactInfo.parent_type=='vendor')",
        uselist=False,
        cascade="all, delete-orphan"
    )

    business_registration_id = Column(Integer, ForeignKey('business_registration.id'), nullable=False)
    timing_id = Column(Integer, ForeignKey('timing.id'), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    contact_info = relationship('ContactInfo', back_populates='vendors')
    physical_address = relationship('PhysicalAddress', back_populates='vendors')
    business_registration = relationship('BusinessRegistration', back_populates='vendors')
    timing = relationship('Timing', back_populates='vendors', single_parent=True)
    opening_days = relationship('OpeningDay', back_populates='vendor', cascade="all, delete-orphan")
    amenities = relationship("Amenity", back_populates="vendors", cascade="all, delete-orphan")
    documents_submitted = relationship('DocumentSubmitted', back_populates='vendor', cascade="all, delete-orphan")
    available_games = relationship('AvailableGame', back_populates='vendor', cascade="all, delete-orphan")
    images = relationship('Image', back_populates='vendor', cascade="all, delete-orphan")  # New relationship

    # One-to-One relationship with VendorCredential
    credential = relationship('VendorCredential', uselist=False, back_populates='vendor', cascade="all, delete")

    # One-to-Many relationship with VendorStatus
    statuses = relationship('VendorStatus', back_populates='vendor', cascade="all, delete")


    def __str__(self):
        return f"Vendor(id={self.id}, cafe_name='{self.cafe_name}', owner_name='{self.owner_name}', description='{self.description}')"

    def __repr__(self):
        return self.__str__()
