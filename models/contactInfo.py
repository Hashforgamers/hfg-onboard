from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.extensions import db

class ContactInfo(db.Model):
    __tablename__ = 'contact_info'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    
    # Foreign Key to Vendor
    parent_id = Column(Integer, ForeignKey('vendors.id'), nullable=False)  # ForeignKey to Vendor
    parent_type = Column(String(50), nullable=False, default='vendor')  # 'vendor' to be used here, no need for polymorphism

    # Relationship to Vendor
    vendor = relationship("Vendor", back_populates="contact_info", foreign_keys=[parent_id])

    def __str__(self):
        return f"ContactInfo(id={self.id}, email='{self.email}', phone='{self.phone}')"