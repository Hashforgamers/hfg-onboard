from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, DateTime, JSON
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db.extensions import db

class Product(db.Model):
    __tablename__ = "products"
    product_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collaborator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('collaborators.collaborator_id'))
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.Enum('energy_drink','energy_bar','mouse','keyboard','mousepad','other', name='product_category_enum'))
    description = db.Column(db.Text)
    unit_price = db.Column(db.Numeric(10,2), nullable=False)
    image_url = Column(String(500), nullable=True)       # Cloudinary image URL
    image_public_id = Column(String(255), nullable=True)
    sku = db.Column(db.String(100), unique=True)
    stock_quantity = db.Column(db.Integer, default=0)
    min_order_quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.Enum('active','inactive', name='product_status_enum'), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    collaborator = db.relationship("Collaborator", back_populates="products")
