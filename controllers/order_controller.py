from flask import Blueprint, request, jsonify , current_app
from db.extensions import db
import uuid
from datetime import datetime
import os
import requests
from models.collaborator import Collaborator
from models.product import Product
from models.vendor import Vendor
from models.order import Order
from models.orderItem import OrderItem
from models.commission import Commission
from models.commission_ledger import CommissionLedger
from models.communication import Communication
from db.extensions import mail
from services.order_notification import NotificationService
from flask_mail import Message
from sqlalchemy.orm import joinedload

order_bp = Blueprint('order', __name__)

DASHBOARD_SERVICE_URL = os.getenv("DASHBOARD_SERVICE_URL", "https://hfg-dashboard.onrender.com")

def _notify_store_updated(vendor_id: int | None = None) -> None:
    try:
        payload = {"vendor_id": int(vendor_id)} if vendor_id else {}
        requests.post(
            f"{DASHBOARD_SERVICE_URL}/internal/ws/store-updated",
            json=payload,
            timeout=3,
        )
    except Exception as e:
        current_app.logger.warning("store_updated notify failed: %s", e)

@order_bp.route('/vendor/products', methods=['GET'])
def vendor_all_products():
    products = Product.query.options(joinedload(Product.collaborator)).filter_by(status='active').all()
    res = []
    for p in products:
        c = p.collaborator
        if c is None:
            continue
        res.append({
            'product_id': str(p.product_id),
            'name': p.name,
            'category': p.category,
            'price': str(p.unit_price),
            'stock': p.stock_quantity,
            'min_order_quantity': p.min_order_quantity,
            'collaborator_id': str(c.collaborator_id),
            'collaborator_brand': c.brand_name,
            'image_url': p.image_url,
            'description': p.description,
        })
    return jsonify(res), 200



@order_bp.route('/orders', methods=['POST'])
def place_order():
    data = request.get_json()
    cafe_id = data['cafe_id']   # vendor.id
    collaborator_id = data['collaborator_id']
    items = data['items']

    if not (cafe_id and collaborator_id and items):
        return jsonify({'error': 'Missing fields'}), 400
    # ... find cafe/vendor, collaborator
    vendor = Vendor.query.get(cafe_id)
    collaborator = Collaborator.query.get(collaborator_id)
    if not vendor or not collaborator:
        return jsonify({'error': 'Invalid vendor/collaborator'}), 400

    total, order_items = 0, []
    for item in items:
        product = Product.query.get(item['product_id'])
        qty = int(item['quantity'])
        if not product or qty < product.min_order_quantity or qty > product.stock_quantity:
            return jsonify({'error': 'Invalid quantity or product'}), 400
        subtotal = float(product.unit_price) * qty
        total += subtotal
        order_items.append({'product': product, 'qty': qty, 'subtotal': subtotal})
        product.stock_quantity -= qty

    commission_amt = (total * float(collaborator.commission_value)/100.0 if collaborator.commission_type == 'percentage'
                      else float(collaborator.commission_value))

    order = Order(
        cafe_id = cafe_id,
        collaborator_id = collaborator_id,
        order_date = datetime.utcnow(),
        status = 'pending',
        total_amount = total,
        commission_amount = commission_amt
    )
    db.session.add(order)
    db.session.flush()
    for oi in order_items:
        db.session.add(OrderItem(
            order_id = order.order_id,
            product_id = oi['product'].product_id,
            quantity = oi['qty'],
            unit_price = oi['product'].unit_price,
            subtotal = oi['subtotal']
        ))
    db.session.add(Commission(
        order_id = order.order_id,
        collaborator_id = collaborator_id,
        commission_type = collaborator.commission_type,
        commission_value = collaborator.commission_value,
        commission_amount = commission_amt
    ))
    db.session.add(CommissionLedger(
        collaborator_id = collaborator_id,
        order_id = order.order_id,
        commission_amount = commission_amt,
        order_amount = total,
        status = 'unpaid'
    ))
    db.session.commit()
    NotificationService.send_order_notification_email(order.order_id)
    _notify_store_updated(cafe_id)
    return jsonify({'order_id': str(order.order_id)}), 201




@order_bp.route('/vendors/<int:vendor_id>/orders', methods=['GET'])
def list_vendor_orders(vendor_id):
    """Marketplace orders a cafe placed with collaborators, newest first."""
    orders = Order.query.filter_by(cafe_id=vendor_id).order_by(Order.order_date.desc()).all()
    if not orders:
        return jsonify([]), 200

    order_ids = [o.order_id for o in orders]
    collaborator_ids = {o.collaborator_id for o in orders if o.collaborator_id}
    collaborators = {
        c.collaborator_id: c
        for c in Collaborator.query.filter(Collaborator.collaborator_id.in_(collaborator_ids)).all()
    } if collaborator_ids else {}
    items = OrderItem.query.filter(OrderItem.order_id.in_(order_ids)).all()
    product_ids = {i.product_id for i in items if i.product_id}
    products = {
        p.product_id: p
        for p in Product.query.filter(Product.product_id.in_(product_ids)).all()
    } if product_ids else {}

    items_by_order = {}
    for item in items:
        product = products.get(item.product_id)
        items_by_order.setdefault(item.order_id, []).append({
            "product_id": str(item.product_id) if item.product_id else None,
            "product_name": product.name if product else "Removed product",
            "image_url": product.image_url if product else None,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price or 0),
            "subtotal": float(item.subtotal or 0),
        })

    result = []
    for order in orders:
        collaborator = collaborators.get(order.collaborator_id)
        result.append({
            "order_id": str(order.order_id),
            "collaborator_id": str(order.collaborator_id) if order.collaborator_id else None,
            "collaborator_name": collaborator.name if collaborator else "Unknown",
            "collaborator_brand": collaborator.brand_name if collaborator else None,
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            "status": order.status,
            "total_amount": float(order.total_amount or 0),
            "commission_amount": float(order.commission_amount or 0),
            "items": items_by_order.get(order.order_id, []),
        })

    return jsonify(result), 200
