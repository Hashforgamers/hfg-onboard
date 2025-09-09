from sqlalchemy import Column, Integer, String, Text, Date, Float, Boolean, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from db.extensions import db

class OrderItem(db.Model):
    __tablename__ = "order_items"
    order_item_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = db.Column(UUID(as_uuid=True), db.ForeignKey('orders.order_id'))
    product_id = db.Column(UUID(as_uuid=True), db.ForeignKey('products.product_id'))
    quantity = db.Column(db.Integer)
    unit_price = db.Column(db.Numeric(10,2))
    subtotal = db.Column(db.Numeric(10,2))
    order = db.relationship("Order", back_populates="items")