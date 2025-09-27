from flask import Blueprint, request, jsonify , current_app
from db.extensions import db
import uuid
from datetime import datetime
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

order_bp = Blueprint('order', __name__)

@order_bp.route('/vendor/products', methods=['GET'])
def vendor_all_products():
    products = Product.query.filter_by(status='active').all()
    res = []
    for p in products:
        c = Collaborator.query.get(p.collaborator_id)
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
    return jsonify({'order_id': str(order.order_id)}), 201




@order_bp.route('/vendors/<int:vendor_id>/orders', methods=['GET'])
def list_vendor_orders(vendor_id):
    orders = Order.query.filter_by(cafe_id=vendor_id).order_by(Order.order_date.desc()).all()

    result = []
    for order in orders:
        collaborator = Collaborator.query.get(order.collaborator_id)
        items = OrderItem.query.filter_by(order_id=order.order_id).all()
        
        item_list = []
        for item in items:
            product = Product.query.get(item.product_id)
            item_list.append({
                "product_id": str(product.product_id),
                "product_name": product.name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.subtotal)
            })

        result.append({
            "order_id": str(order.order_id),
            "collaborator_id": str(order.collaborator_id),
            "collaborator_name": collaborator.name if collaborator else "Unknown",
            "order_date": order.order_date.isoformat(),
            "status": order.status,
            "total_amount": float(order.total_amount),
            "commission_amount": float(order.commission_amount),
            "items": item_list
        })

    return jsonify(result), 200
