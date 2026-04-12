# app/__init__.py

import logging
import os
import time
import uuid
from flask import Flask, request, g
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from .config import Config
from db.extensions import db, migrate, mail, redis_client
from controllers.controllers import vendor_bp
from controllers.super_admin_controller import super_admin_bp
from controllers.vendor_games import vendor_games_bp
from controllers.collaborator_controller import collaborator_bp
from controllers.order_controller import order_bp


def _is_insecure_secret(value: str, placeholders: set[str]) -> bool:
    if not value:
        return True
    candidate = str(value).strip()
    if candidate in placeholders:
        return True
    return len(candidate) < 32


def _validate_production_config(app: Flask) -> None:
    app_env = str(app.config.get("APP_ENV", "development")).lower()
    is_production = app_env in {"prod", "production"}
    if not is_production:
        return
    insecure_secret = _is_insecure_secret(
        app.config.get("SECRET_KEY", ""),
        {"your_secret_key", "dev-secret-change-me", "changeme"},
    )
    if insecure_secret:
        raise RuntimeError(
            "In production, SECRET_KEY must be set to a strong non-default value with length >= 32."
        )


def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    _validate_production_config(app)
    if app.config.get("TRUST_PROXY", True):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
    
    # CORS: allow any origin (no credentials) for dashboard/app clients
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allow_headers=['Content-Type', 'Authorization'],
        supports_credentials=False,
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
    app.register_blueprint(super_admin_bp, url_prefix='/api')
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
        g.request_start = time.perf_counter()
        request.start_time = time.time()
        g.request_id = (
            request.headers.get("X-Request-Id")
            or request.headers.get("X-Correlation-Id")
            or str(uuid.uuid4())
        )
        if debug_mode:
            app.logger.debug(f"🚀 Started {request.method} {request.path}")
    
    @app.after_request
    def after_request(response):
        response.headers["X-Request-Id"] = getattr(g, "request_id", "")
        if hasattr(request, 'start_time'):
            elapsed = (time.time() - request.start_time) * 1000
            if app.config.get("API_ENABLE_TIMING_HEADERS", True):
                response.headers["X-Response-Time-Ms"] = f"{elapsed:.2f}"
            response.headers.setdefault(
                "Cache-Control",
                app.config.get("API_DEFAULT_CACHE_CONTROL", "no-store"),
            )
            
            # Log slow requests (over 500ms)
            slow_ms = int(app.config.get("API_SLOW_REQUEST_MS", 120) or 120)
            if elapsed > slow_ms:
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
        # Keep HTTP errors (404/405/etc.) as-is instead of masking as 500.
        if isinstance(e, HTTPException):
            return {
                'success': False,
                'message': e.description,
                'code': e.code,
            }, e.code
        app.logger.error(f"❌ Unhandled exception: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': 'Internal server error. Please try again.'
        }, 500

    @app.route('/', methods=['GET', 'HEAD'])
    def root():
        return {'status': 'ok', 'service': 'hfg-onboard'}, 200
    
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
