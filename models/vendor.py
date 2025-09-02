from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from db.extensions import db
from datetime import datetime
from models.amenity import Amenity
from models.documentSubmitted import DocumentSubmitted
from models.openingDay import OpeningDay
from models.availableGame import AvailableGame
from models.passwordManager import PasswordManager
from models.vendorStatus import VendorStatus
from models.physicalAddress import PhysicalAddress
from models.contactInfo import ContactInfo
from models.businessRegistration import BusinessRegistration
from models.timing import Timing
from models.vendorAccount import VendorAccount
from models.vendorPin import VendorPin
from sqlalchemy import Text


class Vendor(db.Model):
    __tablename__ = 'vendors'
    
    id = Column(Integer, primary_key=True)
    cafe_name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Foreign Key to BusinessRegistration
    business_registration_id = Column(Integer, ForeignKey('business_registration.id'), nullable=True)
    # Foreign Key to Timing
    timing_id = Column(Integer, ForeignKey('timing.id'), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

   # Relationship to PhysicalAddress
    physical_address = relationship(
        'PhysicalAddress',
        back_populates='vendor',
        uselist=False,  # One-to-one relationship
        cascade="all, delete-orphan"
    )

    # Relationship to ContactInfo
    # contact_info = relationship("ContactInfo", back_populates="vendor", uselist=False)
    # Relationship to ContactInfo
    # Relationship to ContactInfo
    contact_info = relationship(
        "ContactInfo",
        back_populates="vendor",  # Ensure this matches the relationship in ContactInfo
        uselist=False,
        cascade="all, delete"
    )

    __mapper_args__ = {
        'polymorphic_identity': 'vendor',  # Only 'vendor' here
    }

    # Relationship to BusinessRegistration
    business_registration = relationship('BusinessRegistration', back_populates='vendors')

    # Relationship to Timing
    timing = relationship('Timing', back_populates='vendors', single_parent=True)

    # Relationship to OpeningDay
    opening_days = relationship(
        'OpeningDay',
        back_populates='vendor',
        cascade="all, delete-orphan"
    )

    # Relationship to Amenity
    amenities = relationship(
        "Amenity",
        back_populates="vendors",
        cascade="all, delete-orphan"
    )

    # Relationship to DocumentSubmitted
    documents_submitted = relationship(
        'DocumentSubmitted',
        back_populates='vendor',
        cascade="all, delete-orphan"
    )
    
        # ADDED: Relationship to Document (for Cloudinary documents)
    documents = relationship(
        'Document',
        back_populates='vendor',
        cascade="all, delete-orphan"
    )


    # Relationship to AvailableGame
    available_games = relationship(
        'AvailableGame',
        back_populates='vendor',
        cascade="all, delete-orphan"
    )

    # Relationship to Image (new addition)
    images = relationship(
        'Image',
        back_populates='vendor',
        cascade="all, delete-orphan"
    )

       # One-to-One relationship with VendorCredential
    credential = None

    # PasswordManager relationship
    password = relationship(
        'PasswordManager',
        primaryjoin="and_(foreign(PasswordManager.parent_id) == Vendor.id, PasswordManager.parent_type == 'vendor')",
        back_populates='vendor',
        uselist=False,
        cascade="all, delete-orphan"
    )

    payment_methods = relationship('PaymentVendorMap', back_populates='vendor', cascade='all, delete-orphan')
       
       
    # One-to-Many relationship with VendorStatus
    statuses = relationship(
        'VendorStatus',
        back_populates='vendor',
        cascade="all, delete"
    )

    # In Vendor model
    account_id = Column(Integer, ForeignKey('vendor_accounts.id'), nullable=True)
    account = relationship('VendorAccount', back_populates='vendors')

    pin = relationship('VendorPin', back_populates='vendor', uselist=False, cascade="all, delete-orphan")

    # Added new Vendor model
    supported_games = relationship(
        'SupportedGame',
        back_populates='vendor',
        cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"Vendor(id={self.id}, cafe_name='{self.cafe_name}', owner_name='{self.owner_name}', description='{self.description}')"

    def __repr__(self):
        return self.__str__()
