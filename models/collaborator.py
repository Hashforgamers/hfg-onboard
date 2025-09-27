from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, DateTime, JSON
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db.extensions import db


class Invoice(db.Model):
    __tablename__ = "invoices"
    invoice_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collaborator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('collaborators.collaborator_id'))
    invoice_month = db.Column(db.Date)
    total_commission = db.Column(db.Numeric(10,2))
    total_orders = db.Column(db.Numeric(10,2))
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)
    status = db.Column(db.Enum('draft','sent','paid', name='invoice_status_enum'), default='draft')
    pdf_url = db.Column(db.String(500))
    collaborator = db.relationship("Collaborator", back_populates="invoices")

class Collaborator(db.Model):
    __tablename__ = 'collaborators'
    collaborator_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=False)
    brand_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30))
    address = db.Column(db.Text)
    website = db.Column(db.String(255))
    commission_type = db.Column(db.Enum('percentage', 'fixed', name='commission_type_enum'), nullable=False)
    commission_value = db.Column(db.Numeric(10, 2), nullable=False)
    min_order_quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.Enum('active', 'inactive', name='collaborator_status_enum'), default='active')
    products = db.relationship("Product", back_populates="collaborator")
    communications = db.relationship("Communication", back_populates="collaborator")
    invoices = db.relationship("Invoice", back_populates="collaborator")
