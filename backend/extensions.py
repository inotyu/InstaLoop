from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import redis
import os

def _rate_limit_key():
    from flask import request
    try:
        from utils.fingerprint import generate_fingerprint
        fp = generate_fingerprint(request)
    except Exception:
        fp = ''
    return f"{get_remote_address()}:{fp}"

# Inicializa extensões
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

# Redis para rate limiting
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# Rate limiter
limiter = Limiter(
    key_func=_rate_limit_key,
    storage_uri=os.environ.get('RATELIMIT_STORAGE_URL', 'memory://'),
    default_limits=["300 per minute"]
)
