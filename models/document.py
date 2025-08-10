from db.extensions import db

from datetime import datetime
from sqlalchemy.orm import relationship


class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    document_type = db.Column(db.String(100), nullable=False)
    document_url = db.Column(db.String(500), nullable=False)   # Cloudinary URL
    public_id = db.Column(db.String(255), nullable=True)       # Cloudinary public_id
    #file_path = db.Column(db.String(255), nullable=False)  # Can store Google Drive URL or File ID
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    status = db.Column(db.String(20), default='unverified')  # New field for verification status
    
    # Relationship back to Vendor
    vendor = relationship('Vendor', back_populates='documents')
    
    def __str__(self):
        return f"<Document {self.document_type} for Vendor {self.vendor_id}>"

    def __repr__(self):
        return self.__str__()