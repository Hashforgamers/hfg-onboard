# app/config.py

import os
from datetime import timedelta

class Config:
    # Flask Secret Key
    SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URI',
        'postgresql://postgres:postgres@db:5432/vendor_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # OPTIMIZED: Database connection pool configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,       # Validate connections before using
        "pool_recycle": 1800,        # Recycle every 30 minutes
        "pool_size": 10,             # Maintain 10 connections
        "max_overflow": 20,          # Allow 20 extra connections
        "pool_timeout": 30,          # Wait 30s for available connection
        "connect_args": {
            "connect_timeout": 10,   # PostgreSQL connection timeout
            "options": "-c statement_timeout=30000"  # 30s query timeout
        }
    }

    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit
    
    # Mail Configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.hashforgamers.co.in")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ("true", "1", "t")
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in ("true", "1", "t")
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "no-reply@hashforgamers.co.in")
    MAIL_MAX_EMAILS = None
    MAIL_ASCII_ATTACHMENTS = False
    
    # Redis Configuration (for direct access via redis_client)
    REDIS_URL = os.getenv('REDIS_URL')
    REDIS_TLS_ENABLED = os.getenv('REDIS_TLS_ENABLED', 'false').lower() == 'true'

    # Google Drive Configuration
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')
