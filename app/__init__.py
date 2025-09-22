# app/__init__.py

import logging
import os
from flask import Flask
from flask_cors import CORS
from .config import Config
from db.extensions import db, migrate, mail
from controllers.controllers import vendor_bp
from controllers.vendor_games import vendor_games_bp
from controllers.collaborator_controller import collaborator_bp
from controllers.order_controller import order_bp

def create_app():
    app = Flask(__name__)
    CORS(app, origins=["http://localhost:3000" ,"http://localhost:3001", "https://dashboard.hashforgamers.co.in" , "https://dev-dashboard.hashforgamers.co.in", "https://vendor-onboard-zeta.vercel.app" ],
          methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
     allow_headers=['Content-Type', 'Authorization']
         )
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Register blueprints
    app.register_blueprint(vendor_bp, url_prefix='/api')
    app.register_blueprint(vendor_games_bp, url_prefix='/api')
    app.register_blueprint(collaborator_bp , url_prefix='/api')
    app.register_blueprint(order_bp, url_prefix='/api')

    # Configure logging
    debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
    log_level = logging.DEBUG if debug_mode else logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Ensure that the Flask app logger uses this configuration
    app.logger.setLevel(log_level)
    
    return app
