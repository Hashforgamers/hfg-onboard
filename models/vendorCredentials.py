# models/vendorCredentials.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from db.extensions import db

class VendorCredential():
    pass
    # __tablename__ = 'vendor_credentials'
    
    # id = Column(Integer, primary_key=True)
    # vendor_id = Column(Integer, ForeignKey('vendors.id'), nullable=False, unique=True)
    # username = Column(String, nullable=False, unique=True)
    # password_hash = Column(String, nullable=False)

    # # Link to Vendor model
    # vendor = relationship('Vendor', back_populates='credential')

    # def __str__(self):
    #     return f"VendorCredential(id={self.id}, vendor_id='{self.vendor_id}', username={self.username}, password_hash='{self.password_hash}')"

    # def __repr__(self):
    #     return self.__str__()
