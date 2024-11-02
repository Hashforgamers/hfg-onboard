from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.extensions import db
from models.amenity import Amenity
from models.documentSubmitted import DocumentSubmitted
from models.openingDay import OpeningDay
from models.availableGame import AvailableGame

class Vendor(db.Model):
    __tablename__ = 'vendors'
    
    id = Column(Integer, primary_key=True)
    cafe_name = Column(String(255), nullable=False)
    owner_name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)

    contact_info_id = Column(Integer, ForeignKey('contact_info.id'), nullable=False)
    physical_address_id = Column(Integer, ForeignKey('physical_address.id'), nullable=False)
    business_registration_id = Column(Integer, ForeignKey('business_registration.id'), nullable=False)
    timing_id = Column(Integer, ForeignKey('timing.id'), nullable=False)

    # Relationships
    contact_info = relationship('ContactInfo', back_populates='vendors')
    physical_address = relationship('PhysicalAddress', back_populates='vendors')
    business_registration = relationship('BusinessRegistration', back_populates='vendors')
    timing = relationship('Timing', back_populates='vendors', single_parent=True)
    opening_days = relationship('OpeningDay', back_populates='vendor', cascade="all, delete-orphan")
    amenities = relationship("Amenity", back_populates="vendors", cascade="all, delete-orphan")
    documents_submitted = relationship('DocumentSubmitted', back_populates='vendor', cascade="all, delete-orphan")
    available_games = relationship('AvailableGame', back_populates='vendor', cascade="all, delete-orphan")

    def __str__(self):
        return f"Vendor(id={self.id}, cafe_name='{self.cafe_name}', owner_name='{self.owner_name}', description='{self.description}')"

    def __repr__(self):
        return self.__str__()
