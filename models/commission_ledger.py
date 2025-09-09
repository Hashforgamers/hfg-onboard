from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, DateTime, JSON
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db.extensions import db

class CommissionLedger(db.Model):
    __tablename__ = "commission_ledger"
    ledger_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collaborator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('collaborators.collaborator_id'))
    order_id = db.Column(UUID(as_uuid=True), db.ForeignKey('orders.order_id'))
    commission_amount = db.Column(db.Numeric(10,2))
    order_amount = db.Column(db.Numeric(10,2))
    entry_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum('unpaid','invoiced','paid', name='ledger_status_enum'), default='unpaid')
    invoice_id = db.Column(UUID(as_uuid=True), nullable=True)