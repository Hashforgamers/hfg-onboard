# app/utils.py

import string
import random
from flask_mail import Message
from db.extensions import mail
from flask import current_app

def generate_credentials(length=8):
    letters = string.ascii_letters
    digits = string.digits
    username = ''.join(random.choice(letters) for i in range(6))
    password = ''.join(random.choice(letters + digits) for i in range(length))
    return username, password

def send_email(subject, recipients, body):
    msg = Message(subject, recipients=recipients)
    msg.body = body
    mail.send(msg)
