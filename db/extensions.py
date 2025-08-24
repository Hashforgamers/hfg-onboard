# app/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
import os
import redis
import urllib.parse

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()

# Redis client configuration for external Redis
def create_redis_client():
    redis_url = os.getenv('REDIS_URL')
    use_tls = os.getenv('REDIS_TLS_ENABLED', 'false').lower() == 'true'
    
    if redis_url:
        parsed = urllib.parse.urlparse(redis_url)
        return redis.Redis(
            host=parsed.hostname,
            port=parsed.port or 6379,
            username=parsed.username,
            password=parsed.password,
            ssl=use_tls,
            ssl_cert_reqs=None,  # For managed Redis services
            decode_responses=True
        )
    else:
        # Fallback for local development
        return redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )

redis_client = create_redis_client()
