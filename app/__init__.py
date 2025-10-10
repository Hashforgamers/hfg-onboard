# app/__init__.py

import logging
import os
import time
from flask import Flask, request
from flask_cors import CORS
from .config import Config
from db.extensions import db, migrate, mail, redis_client
from controllers.controllers import vendor_bp
from controllers.vendor_games import vendor_games_bp
from controllers.collaborator_controller import collaborator_bp
from controllers.order_controller import order_bp


def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # CRITICAL: CORS with credentials support
    CORS(app, 
         origins=[
             "http://localhost:3000", 
             "http://localhost:3001", 
             "https://dashboard.hashforgamers.co.in", 
             "https://dev-dashboard.hashforgamers.co.in", 
             "https://vendor-onboard-zeta.vercel.app"
         ],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
         allow_headers=['Content-Type', 'Authorization'],
         supports_credentials=True,  # Enable credentials for auth
         expose_headers=['Content-Type', 'Authorization'],
         max_age=3600
    )
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    # Note: No Session(app) needed - we use Redis directly!
    
    # Register blueprints
    app.register_blueprint(vendor_bp, url_prefix='/api')
    app.register_blueprint(vendor_games_bp, url_prefix='/api')
    app.register_blueprint(collaborator_bp, url_prefix='/api')
    app.register_blueprint(order_bp, url_prefix='/api')

    # Configure logging
    debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
    log_level = logging.DEBUG if debug_mode else logging.INFO
    logging.basicConfig(
        level=log_level, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    app.logger.setLevel(log_level)
    
    # Request timing middleware for performance monitoring
    @app.before_request
    def before_request():
        request.start_time = time.time()
        if debug_mode:
            app.logger.debug(f"🚀 Started {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        if hasattr(request, 'start_time'):
            elapsed = (time.time() - request.start_time) * 1000
            
            # Log slow requests (over 500ms)
            if elapsed > 500:
                app.logger.warning(
                    f"⚠️  SLOW REQUEST: {request.method} {request.path} "
                    f"took {elapsed:.2f}ms - Status: {response.status_code}"
                )
            elif debug_mode:
                app.logger.info(
                    f"✅ {request.method} {request.path} "
                    f"took {elapsed:.2f}ms - Status: {response.status_code}"
                )
        
        return response
    
    # Global error handler
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f"❌ Unhandled exception: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': 'Internal server error. Please try again.'
        }, 500
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint for monitoring"""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            
            # Test Redis connection
            redis_client.ping()
            
            return {
                'status': 'ok',
                'database': 'connected',
                'redis': 'connected',
                'timestamp': time.time()
            }, 200
        except Exception as e:
            app.logger.error(f"❌ Health check failed: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'timestamp': time.time()
            }, 500
    
    return app
