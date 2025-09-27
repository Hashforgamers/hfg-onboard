from flask import Blueprint, request, jsonify , current_app
from db.extensions import db
import uuid
from datetime import datetime
from models.collaborator import Collaborator
from models.product import Product
from services.cloudinary_services import CloudinaryGameImageService

collaborator_bp = Blueprint('collaborator', __name__)

@collaborator_bp.route('/collaborators', methods=['POST'])
def create_collaborator():
    data = request.get_json()
    try:
        c = Collaborator(
            collaborator_id = uuid.uuid4(),
            name = data['name'],
            brand_name = data['brand_name'],
            email = data['email'],
            phone = data.get('phone'),
            address = data.get('address'),
            website = data.get('website'),
            commission_type = data['commission_type'],
            commission_value = data['commission_value'],
            min_order_quantity = data['min_order_quantity'],
            status = data.get('status', 'active'),
            created_at = datetime.utcnow(),
            updated_at = datetime.utcnow()
        )
        db.session.add(c)
        db.session.commit()
        return jsonify({'collaborator_id': str(c.collaborator_id)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@collaborator_bp.route('/collaborators', methods=['GET'])
def list_collaborators():
    collaborators = Collaborator.query.all()
    res = []
    for c in collaborators:
        res.append({
            'collaborator_id': str(c.collaborator_id),
            'name': c.name,
            'brand_name': c.brand_name,
            'email': c.email,
            'commission_type': c.commission_type,
            'commission_value': str(c.commission_value),
            'min_order_quantity': c.min_order_quantity,
            'status': c.status
        })
    return jsonify(res), 200

@collaborator_bp.route('/collaborators/<uuid:collaborator_id>', methods=['PUT'])
def update_collaborator(collaborator_id):
    c = Collaborator.query.get(collaborator_id)
    if not c:
        return jsonify({'error': 'Not found'}), 404
    data = request.get_json()
    for field in ['name','brand_name','email','phone','address','website','commission_type','commission_value','min_order_quantity','status']:
        if field in data: setattr(c, field, data[field])
    c.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Updated'}), 200

@collaborator_bp.route('/collaborators/<uuid:collaborator_id>', methods=['DELETE'])
def delete_collaborator(collaborator_id):
    c = Collaborator.query.get(collaborator_id)
    if not c:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(c)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200



@collaborator_bp.route('/collaborators/<uuid:collaborator_id>/products', methods=['POST'])
def add_product(collaborator_id):
    c = Collaborator.query.get(collaborator_id)
    if not c:
        return jsonify({'error': 'Collaborator not found'}), 404
    # Handle image separately
    image_file = request.files.get('image')
    image_url, image_id = None, None
    if image_file:
        upload_res = CloudinaryGameImageService.upload_collaborator_product_image(
            image_file, request.form['name'], c.brand_name
        )
        if not upload_res['success']:
            return jsonify({'error': upload_res['error']}), 400
        image_url, image_id = upload_res['url'], upload_res['public_id']
    data = dict(request.form)
    p = Product(
        product_id = uuid.uuid4(),
        collaborator_id = collaborator_id,
        name = data['name'],
        category = data.get('category', 'other'),
        description = data.get('description'),
        unit_price = data['unit_price'],
        sku = data.get('sku'),
        stock_quantity = data['stock_quantity'],
        min_order_quantity = data.get('min_order_quantity', 1),
        status = data.get('status', 'active'),
        image_url = image_url,
        image_public_id = image_id,
        created_at = datetime.utcnow(),
        updated_at = datetime.utcnow()
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'product_id': str(p.product_id)}), 201

@collaborator_bp.route('/collaborators/<uuid:collaborator_id>/products', methods=['GET'])
def list_products(collaborator_id):
    products = Product.query.filter_by(collaborator_id=collaborator_id).all()
    res = []
    for p in products:
        res.append({
            'product_id': str(p.product_id),
            'name': p.name,
            'category': p.category,
            'unit_price': str(p.unit_price),
            'stock_quantity': p.stock_quantity,
            'min_order_quantity': p.min_order_quantity,
            'description': p.description,
            'status': p.status,
            'image_url': p.image_url,
            'sku': p.sku,
        })
    return jsonify(res), 200

@collaborator_bp.route('/products/<uuid:product_id>', methods=['PUT'])
def update_product(product_id):
    p = Product.query.get(product_id)
    if not p:
        return jsonify({'error': 'Not found'}), 404
    data = request.get_json()
    for field in ['name','category','description','unit_price','sku','stock_quantity','min_order_quantity','status']:
        if field in data: setattr(p, field, data[field])
    p.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Updated'}), 200

@collaborator_bp.route('/products/<uuid:product_id>', methods=['DELETE'])
def delete_product(product_id):
    p = Product.query.get(product_id)
    if not p:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200
