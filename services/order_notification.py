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
            <table style="width:100%; border-collapse:collapse; margin-bottom:15px;">
                <tr>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Product</th>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Qty</th>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Unit Price</th>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Subtotal</th>
                </tr>"""
            for item in items:
                p = Product.query.get(item.product_id)
                items_table += f"""
                <tr>
                    <td style="border:1px solid #ddd; padding:8px;">{p.name}</td>
                    <td style="border:1px solid #ddd; padding:8px; text-align:center;">{item.quantity}</td>
                    <td style="border:1px solid #ddd; padding:8px; text-align:right;">₹{float(item.unit_price):.2f}</td>
                    <td style="border:1px solid #ddd; padding:8px; text-align:right;">₹{float(item.subtotal):.2f}</td>
                </tr>"""
            items_table += "</table>"

            # Order summary table (HTML)
            order_summary_table = f"""
            <table style="width:100%; border-collapse:collapse; margin-bottom:15px;">
                <tr>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Total Amount</th>
                    <td style="border:1px solid #ddd; padding:8px; text-align:right;">₹{float(order.total_amount):.2f}</td>
                </tr>
                <tr>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Commission (HashForGamers)</th>
                    <td style="border:1px solid #ddd; padding:8px; text-align:right;">₹{float(order.commission_amount):.2f}</td>
                </tr>
                <tr>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Net Payable to You</th>
                    <td style="border:1px solid #ddd; padding:8px; text-align:right; font-weight:bold;">₹{float(order.total_amount) - float(order.commission_amount):.2f}</td>
                </tr>
            </table>
            """

            # Main HTML body
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Order Notification</title>
    <style>
        body {{ font-family: Arial, sans-serif; color: #222; background: #fff; }}
        .main {{ max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; }}
        h1 {{ font-size: 20px; margin-bottom: 0.5em; }}
        h2 {{ font-size: 16px; margin-top: 2em; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        p {{ margin-top: 0.4em; margin-bottom: 0.4em; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 15px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 14px; }}
        th {{ background: #f3f3f3; text-align: left; font-weight: bold; }}
        .footer {{ color: #888; font-size: 11px; text-align: center; border-top: 1px solid #eee; margin-top: 30px; padding-top: 8px; }}
    </style>
</head>
<body>
<div class="main">
    <h1>Order Confirmation</h1>
    <p>Dear {collaborator.name},</p>
    <p>Your order has been received on {order.order_date.strftime('%Y-%m-%d %H:%M')}. Below are the details:</p>
    <h2>Order & Cafe Info</h2>
    <table>
        <tr><th>Order ID</th><td>{order.order_id}</td></tr>
        <tr><th>Status</th><td>{order.status.capitalize()}</td></tr>
        <tr><th>Cafe Name</th><td>{vendor.cafe_name}</td></tr>
        <tr><th>Owner</th><td>{vendor.owner_name}</td></tr>
        <tr><th>Email</th><td>{vendor_email}</td></tr>
        <tr><th>Phone</th><td>{vendor_phone}</td></tr>
    </table>
    <h2>Products</h2>
    {items_table}
    <h2>Payment Summary</h2>
    {order_summary_table}
    <p><b>Note:</b> Min order quantity: {collaborator.min_order_quantity} units.<br>
    Please review your order and confirm within 24 hours. </p>
    <p>For help, reply or write to: <a href="mailto:support@hashfogamings.com">support@hashfogamings.com</a></p>
    <div class="footer">
        HashForGamers &copy; {order.order_date.year} | This is an automated message.
    </div>
</div>
</body>
</html>
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

For help, email support@hashfogamings.com

HashForGamers © {order.order_date.year}
"""

            msg = Message(
                subject, 
                recipients=[collaborator.email],
                cc=['bhanu.joshi@hashforgamers.com' , 'Zeyan.ansari@hashforgamers.com'], 
                body=text_body,
                html=html_body
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
            subject = f"🧾 Monthly Commission Invoice – HashForGamers"
            invoice_table = f"""
            <table style="width:100%; border-collapse:collapse; margin-bottom:15px;">
                <tr>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Invoice ID</th>
                    <td style="border:1px solid #ddd; padding:8px;">{invoice_data.get('invoice_id')}</td>
                </tr>
                <tr>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Total Commission</th>
                    <td style="border:1px solid #ddd; padding:8px;">₹{invoice_data.get('total_commission', 0):.2f}</td>
                </tr>
                <tr>
                    <th style="border:1px solid #ddd; padding:8px; background:#f3f3f3;">Due Date</th>
                    <td style="border:1px solid #ddd; padding:8px;">{invoice_data.get('due_date')}</td>
                </tr>
            </table>
            """
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Commission Invoice</title>
    <style>
        body {{ font-family: Arial, sans-serif; color: #222; background: #fff; }}
        .main {{ max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; }}
        h1 {{ font-size: 20px; margin-bottom: 0.5em; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 15px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 14px; }}
        th {{ background: #f3f3f3; font-weight: bold; }}
        .footer {{ color: #888; font-size: 11px; text-align: center; border-top: 1px solid #eee; margin-top: 30px; padding-top: 8px; }}
    </style>
</head>
<body>
<div class="main">
    <h1>Commission Invoice</h1>
    <p>Dear {collaborator_name},</p>
    <p>Your monthly commission invoice is ready. Details below:</p>
    {invoice_table}
    <p>Please login to your dashboard to download the invoice and process payment by the due date.</p>
    <div class="footer">
        HashForGamers &copy; {datetime.now().year} | For support: support@hashfogamings.com
    </div>
</div>
</body>
</html>
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
Support: support@hashfogamings.com
"""
            msg = Message(
                subject, 
                recipients=[collaborator_email],
                body=text_body,
                html=html_body
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
