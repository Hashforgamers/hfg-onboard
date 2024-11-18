from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.extensions import db
from models.vendor import Vendor

class ContactInfo(db.Model):
    __tablename__ = 'contact_info'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    
    # Polymorphic fields
    parent_id = Column(Integer, nullable=False)
    parent_type = Column(String(50), nullable=False)

    # Polymorphic relationships
    vendor = relationship("Vendor", back_populates="contact_info", foreign_keys=[parent_id])

    __mapper_args__ = {
        'polymorphic_identity': 'contact_info',
        'polymorphic_on': parent_type
    }
    
    def __str__(self):
        return f"ContactInfo(id={self.id}, email='{self.email}', phone='{self.phone}')"
