# app/config.py

import os


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URI',
        'postgresql://postgres:postgres@db:5432/vendor_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Add safe engine options for Neon / Postgres
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,    # Validate connections before using
        "pool_recycle": 1800,     # Recycle every 30 minutes to avoid SSL timeouts
        "pool_size": 5,           # Maintain small pool (good for Render dynos)
        "max_overflow": 10        # Allow short bursts
    }

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

    # Google Drive
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')  # Path to credentials JSON
    
    # Cloudinary
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')
