# app/config.py

import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://postgres:postgres@db:5432/vendor_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit
    
    # Mail server settings
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.hashforgamers.co.in")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))  # Use 587 for TLS
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "1", "t")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in ("true", "1", "t")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")  # Your SMTP username
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")  # Your SMTP password
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "no-reply@hashforgamers.co.in")

    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')  # Path to credentials JSON
