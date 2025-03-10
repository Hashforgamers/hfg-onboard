# app/__init__.py

import logging
import os
from flask import Flask
from .config import Config
from db.extensions import db, migrate, mail
from controllers.controllers import vendor_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Register blueprints
    app.register_blueprint(vendor_bp, url_prefix='/api')

    # Configure logging
    debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
    log_level = logging.DEBUG if debug_mode else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Ensure that the Flask app logger uses this configuration
    app.logger.setLevel(log_level)
    
    return app
