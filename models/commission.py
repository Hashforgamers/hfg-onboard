from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, DateTime, JSON
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db.extensions import db

class Commission(db.Model):
    __tablename__ = "commissions"
    commission_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = db.Column(UUID(as_uuid=True), db.ForeignKey('orders.order_id'))
    collaborator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('collaborators.collaborator_id'))
    commission_type = db.Column(db.Enum('percentage','fixed', name='commission_type_enum'))
    commission_value = db.Column(db.Numeric(10,2))
    commission_amount = db.Column(db.Numeric(10,2))
    payout_status = db.Column(db.Enum('pending','paid', name='payout_status_enum'), default='pending')
    payout_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    order = db.relationship("Order", back_populates="commission")