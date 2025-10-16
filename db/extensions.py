# db/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
import os
import redis
from redis.connection import ConnectionPool, SSLConnection
import urllib.parse
import logging

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()

logger = logging.getLogger(__name__)


def create_redis_pool():
    """
    Create a Redis connection pool to reuse connections
    This prevents repeated SSL handshakes which cause 10+ second delays
    """
    redis_url = os.getenv('REDIS_URL')
    use_tls = os.getenv('REDIS_TLS_ENABLED', 'false').lower() == 'true'
    
    if redis_url:
        parsed = urllib.parse.urlparse(redis_url)
        
        # Connection pool configuration
        pool_kwargs = {
            'host': parsed.hostname,
            'port': parsed.port or 6379,
            'username': parsed.username,
            'password': parsed.password,
            'decode_responses': True,
            'socket_connect_timeout': 10,   # Increased for SSL handshake
            'socket_timeout': 5,
            'socket_keepalive': True,
            'retry_on_timeout': True,
            'retry_on_error': [
                redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError
            ],
            'health_check_interval': 30,
            'max_connections': 50,          # Connection pool size
        }
        
        # Add SSL configuration
        if use_tls or parsed.scheme == 'rediss':
            pool_kwargs.update({
                'connection_class': SSLConnection,
                'ssl': True,
                'ssl_cert_reqs': None,
                'ssl_check_hostname': False,
            })
            logger.info("✅ Redis pool with SSL/TLS enabled")
        
        try:
            pool = ConnectionPool(**pool_kwargs)
            logger.info(f"✅ Redis connection pool created: {parsed.hostname}")
            return pool
        except Exception as e:
            logger.error(f"❌ Failed to create Redis pool: {str(e)}")
            raise
    else:
        # Local development
        logger.info("🔧 Local Redis pool")
        return ConnectionPool(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            max_connections=20,
        )


# Create connection pool ONCE at startup
redis_pool = create_redis_pool()

# Create Redis client using the pool (reuses connections)
redis_client = redis.Redis(connection_pool=redis_pool)


def check_redis_health():
    """Check Redis connection health"""
    try:
        redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"❌ Redis health check failed: {str(e)}")
        return False


# Pre-warm the connection pool on startup
try:
    logger.info("🔄 Pre-warming Redis connection pool...")
    redis_client.ping()
    logger.info("✅ Redis connection pool ready")
except Exception as e:
    logger.warning(f"⚠️  Redis pre-warm failed (will retry on first request): {str(e)}")
