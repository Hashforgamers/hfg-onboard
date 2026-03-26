from flask import current_app
from flask_mail import Message
from db.extensions import db
from models.order import Order
from models.collaborator import Collaborator
from models.vendor import Vendor
from models.orderItem import OrderItem
from models.product import Product
from models.communication import Communication
from datetime import datetime
from services.email_template import build_hfg_email_html

class NotificationService:
    
    @staticmethod
    def send_order_notification_email(order_id):
        """Send order notification email to collaborator with clean professional HTML."""
        try:
            order = Order.query.get(order_id)
            if not order:
                current_app.logger.error(f"Order {order_id} not found")
                return False

            collaborator = Collaborator.query.get(order.collaborator_id)
            vendor = Vendor.query.get(order.cafe_id)
            items = OrderItem.query.filter_by(order_id=order_id).all()
            
            # Get vendor contact info (filtered by primaryjoin)
            vendor_email = getattr(vendor.contact_info, 'email', 'N/A') if vendor and vendor.contact_info else 'N/A'
            vendor_phone = getattr(vendor.contact_info, 'phone', 'N/A') if vendor and vendor.contact_info else 'N/A'

            subject = f"Order Confirmation - {order.order_id}"
           
            # Products table (HTML)
            items_table = """
            <table style="width:100%; border-collapse:collapse; margin-bottom:15px; border:1px solid #1e2a44; border-radius:8px; overflow:hidden; background:#08142c;">
                <tr>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Product</th>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Qty</th>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Unit Price</th>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Subtotal</th>
                </tr>"""
            for item in items:
                p = Product.query.get(item.product_id)
                items_table += f"""
                <tr>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; color:#e2e8f0;">{p.name}</td>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; text-align:center; color:#e2e8f0;">{item.quantity}</td>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; text-align:right; color:#e2e8f0;">₹{float(item.unit_price):.2f}</td>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; text-align:right; color:#e2e8f0;">₹{float(item.subtotal):.2f}</td>
                </tr>"""
            items_table += "</table>"

            # Order summary table (HTML)
            order_summary_table = f"""
            <table style="width:100%; border-collapse:collapse; margin-bottom:15px; border:1px solid #1e2a44; border-radius:8px; overflow:hidden; background:#08142c;">
                <tr>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Total Amount</th>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; text-align:right; color:#e2e8f0;">₹{float(order.total_amount):.2f}</td>
                </tr>
                <tr>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Commission (Hash For Gamers)</th>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; text-align:right; color:#e2e8f0;">₹{float(order.commission_amount):.2f}</td>
                </tr>
                <tr>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Net Payable to You</th>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; text-align:right; font-weight:bold; color:#22c55e;">₹{float(order.total_amount) - float(order.commission_amount):.2f}</td>
                </tr>
            </table>
            """

            # Main HTML body fragment (wrapped by shared template)
            html_body = f"""
            <p style="margin:0 0 12px 0;color:#e5e7eb;">Dear <strong>{collaborator.name}</strong>,</p>
            <p style="margin:0 0 14px 0;color:#cbd5e1;">
                Your order was received on {order.order_date.strftime('%Y-%m-%d %H:%M')}. Details are below.
            </p>
            <div style="font-size:14px;font-weight:700;color:#22c55e;margin:0 0 8px 0;">Order and Cafe Info</div>
            {order_summary_table}
            <div style="font-size:14px;font-weight:700;color:#22c55e;margin:12px 0 8px 0;">Products</div>
            {items_table}
            <p style="margin:12px 0 8px 0;color:#cbd5e1;">
                <strong>Note:</strong> Minimum order quantity is {collaborator.min_order_quantity} units. Please review and confirm within 24 hours.
            </p>
            <p style="margin:0;color:#94a3b8;">
                For help, reply to this email or write to
                <a href="mailto:support@hashforgamers.co.in" style="color:#60a5fa;text-decoration:none;">support@hashforgamers.co.in</a>.
            </p>
            """

            text_body = f"""
Order Confirmation

Dear {collaborator.name},

Your order has been received on {order.order_date.strftime('%Y-%m-%d %H:%M')}.

Order ID: {order.order_id}
Status: {order.status.capitalize()}
Cafe Name: {vendor.cafe_name}
Owner: {vendor.owner_name}
Email: {vendor_email}
Phone: {vendor_phone}

Products:
""" + "".join([
    f"- {Product.query.get(item.product_id).name}: Qty {item.quantity} x ₹{float(item.unit_price):.2f} = ₹{float(item.subtotal):.2f}\n"
    for item in items
]) + f"""

Total Amount: ₹{order.total_amount:.2f}
Commission: ₹{order.commission_amount:.2f}
Net Payable: ₹{float(order.total_amount) - float(order.commission_amount):.2f}

Min order quantity: {collaborator.min_order_quantity} units.
Please review and confirm your order within 24 hours.

For help, email support@hashforgamers.co.in

HashForGamers © {order.order_date.year}
"""

            msg = Message(
                subject, 
                recipients=[collaborator.email],
                cc=['bhanu.joshi@hashforgamers.com' , 'Zeyan.ansari@hashforgamers.com'], 
                body=text_body,
                html=build_hfg_email_html(
                    subject=subject,
                    content_html=html_body,
                    preview_text=f"Order {order.order_id} confirmation",
                )
            )
            
            mail = current_app.extensions.get('mail')
            if mail:
                mail.send(msg)
                status = 'sent'
            else:
                current_app.logger.error("Flask-Mail not initialized")
                status = 'failed'

            db.session.add(Communication(
                collaborator_id=collaborator.collaborator_id,
                subject=subject,
                body=text_body,
                sent_at=datetime.utcnow(),
                status=status
            ))
            db.session.commit()

            return True

        except Exception as e:
            current_app.logger.error(f"Failed to send order notification: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def send_invoice_notification_email(collaborator_email, collaborator_name, invoice_data):
        """Send invoice notification email with table format"""
        try:
            subject = "Monthly Commission Invoice - Hash For Gamers"
            invoice_table = f"""
            <table style="width:100%; border-collapse:collapse; margin-bottom:15px; border:1px solid #1e2a44; border-radius:8px; overflow:hidden; background:#08142c;">
                <tr>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Invoice ID</th>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; color:#e2e8f0;">{invoice_data.get('invoice_id')}</td>
                </tr>
                <tr>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Total Commission</th>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; color:#e2e8f0;">₹{invoice_data.get('total_commission', 0):.2f}</td>
                </tr>
                <tr>
                    <th style="border-bottom:1px solid #1e2a44; padding:8px; background:#050f23; color:#cbd5e1;">Due Date</th>
                    <td style="border-bottom:1px solid #1e2a44; padding:8px; color:#e2e8f0;">{invoice_data.get('due_date')}</td>
                </tr>
            </table>
            """
            html_body = f"""
            <p style="margin:0 0 12px 0;color:#e5e7eb;">Dear <strong>{collaborator_name}</strong>,</p>
            <p style="margin:0 0 14px 0;color:#cbd5e1;">Your monthly commission invoice is ready.</p>
            {invoice_table}
            <p style="margin:12px 0 0 0;color:#cbd5e1;">
                Please login to your dashboard to download the invoice and process payment by the due date.
            </p>
            <p style="margin:10px 0 0 0;color:#94a3b8;font-size:12px;">
                For support: <a href="mailto:support@hashforgamers.co.in" style="color:#60a5fa;text-decoration:none;">support@hashforgamers.co.in</a>
            </p>
            """
            text_body = f"""
Commission Invoice

Dear {collaborator_name},

Your monthly commission invoice is ready.

Invoice ID: {invoice_data.get('invoice_id')}
Total Commission: ₹{invoice_data.get('total_commission', 0):.2f}
Due Date: {invoice_data.get('due_date')}

Please login to your dashboard to download the invoice and process payment by the due date.

HashForGamers © {datetime.now().year}
Support: support@hashforgamers.co.in
"""
            msg = Message(
                subject, 
                recipients=[collaborator_email],
                body=text_body,
                html=build_hfg_email_html(
                    subject=subject,
                    content_html=html_body,
                    preview_text=f"Invoice {invoice_data.get('invoice_id')}",
                )
            )
            mail = current_app.extensions.get('mail')
            if mail:
                mail.send(msg)
                return True
            else:
                current_app.logger.error("Flask-Mail not initialized")
                return False
        except Exception as e:
            current_app.logger.error(f"Failed to send invoice notification: {e}")
            return False
