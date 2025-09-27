from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, DateTime, JSON
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db.extensions import db

class Order(db.Model):
    __tablename__ = "orders"
    order_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cafe_id = db.Column(db.Integer, db.ForeignKey('vendors.id'))
    collaborator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('collaborators.collaborator_id'))
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('pending','confirmed','shipped','delivered','cancelled', name='order_status_enum'), default='pending')
    total_amount = db.Column(db.Numeric(10,2))
    commission_amount = db.Column(db.Numeric(10,2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    items = db.relationship('OrderItem', back_populates='order')
    commission = db.relationship('Commission', uselist=False, back_populates='order')


