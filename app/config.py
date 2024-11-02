# app/config.py

import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://postgres:postgres@db:5432/vendor_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit
    
    # Webmail SMTP configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.hashforgamers.co.in')  # Update to your webmail SMTP server
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))  # Ensure the port matches your webmail settings
    MAIL_USE_TLS = True  # Use TLS; set to False if using SSL or another method
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')  # Your webmail username (email)
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')  # Your webmail password
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)  # Use the username as default sender if not set
    
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')  # Path to credentials JSON
