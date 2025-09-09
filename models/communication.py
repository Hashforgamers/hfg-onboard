from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db.extensions import db

class Communication(db.Model):
    __tablename__ = "communications"
    comm_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collaborator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('collaborators.collaborator_id'))
    subject = db.Column(db.String(255))
    body = db.Column(db.Text)
    sent_at = db.Column(db.DateTime)
    status = db.Column(db.Enum('sent','failed', name='comm_status_enum'))
    collaborator = db.relationship("Collaborator", back_populates="communications")
