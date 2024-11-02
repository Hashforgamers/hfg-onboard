from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from db.extensions import db

class ContactInfo(db.Model):
    __tablename__ = 'contact_info'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    
    vendors = relationship('Vendor', back_populates='contact_info')

    def __str__(self):
        return f"ContactInfo(id={self.id}, email='{self.email}', phone='{self.phone}')"
