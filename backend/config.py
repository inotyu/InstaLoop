import os
from datetime import timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env (apenas em desenvolvimento)
if not os.environ.get('VERCEL'):
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


def _sqlite_abs_uri(filename: str) -> str:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    path = os.path.join(root, filename)
    return f"sqlite:///{path}"

class Config:
    # Debug logs para identificar problema
    print(f"🔍 CONFIG CLASS - VERCEL: {os.environ.get('VERCEL')}")
    print(f"🔍 CONFIG CLASS - DATABASE_URL from env: {os.environ.get('DATABASE_URL', 'NOT_SET')[:50]}...")
    
    # Banco de dados - PostgreSQL em produção, SQLite em desenvolvimento
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Produção: usar PostgreSQL
        SQLALCHEMY_DATABASE_URI = database_url
        print(f"✅ CONFIG CLASS - Using PostgreSQL: {SQLALCHEMY_DATABASE_URI[:50]}...")
    else:
        # Desenvolvimento: usar SQLite local
        SQLALCHEMY_DATABASE_URI = _sqlite_abs_uri('instaloop.db')
        print(f"❌ CONFIG CLASS - Using SQLite: {SQLALCHEMY_DATABASE_URI}")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 900)))  # 15 min
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 604800)))  # 7 dias
    JWT_ALGORITHM = 'HS256'  # Fixado para evitar algorithm confusion
    
    # Admin
    ADMIN_ROUTE_SECRET = os.environ.get('ADMIN_ROUTE_SECRET')
    
    # Argon2
    ARGON2_TIME_COST = int(os.environ.get('ARGON2_TIME_COST', 3))
    ARGON2_MEMORY_COST = int(os.environ.get('ARGON2_MEMORY_COST', 65536))
    ARGON2_PARALLELISM = int(os.environ.get('ARGON2_PARALLELISM', 2))
    
    # Uploads
    UPLOAD_MAX_SIZE_MB = int(os.environ.get('UPLOAD_MAX_SIZE_MB', 5))
    _UPLOAD_DIR = os.environ.get('UPLOAD_DIR') or 'static/uploads'
    if not os.path.isabs(_UPLOAD_DIR):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        UPLOAD_DIR = os.path.join(root, _UPLOAD_DIR)
    else:
        UPLOAD_DIR = _UPLOAD_DIR
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('RATELIMIT_STORAGE_URL', 'memory://')
    
    # CORS
    CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "http://localhost:5174", "https://insta-loop.vercel.app", "https://insta-loop-iufz.vercel.app"]
    
    # Segurança
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.environ.get('JWT_SECRET_KEY')
    
    # Headers de segurança (serão aplicados via middleware)
    SECURITY_HEADERS = {
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        'X-Frame-Options': 'DENY',
        'X-Content-Type-Options': 'nosniff',
        'Referrer-Policy': 'no-referrer',
        'Permissions-Policy': 'geolocation=(), camera=(), microphone=()',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Resource-Policy': 'cross-origin',
        'Cross-Origin-Embedder-Policy': 'require-corp'
    }
    
    # Arquivos sensíveis bloqueados
    SENSITIVE_FILES = [
        '.env', '.git', 'config.py', 'requirements.txt',
        'docker-compose.yml', 'Dockerfile', '.htaccess',
        'web.config', 'settings.py', '__pycache__'
    ]
    
    # Rotas honeypot
    HONEYPOT_ROUTES = [
        '/admin', '/dashboard', '/cms', '/painel',
        '/wp-admin', '/wp-login.php', '/administrator',
        '/login-admin', '/api/admin', '/api/v1/admin',
        '/api/v2/admin', '/phpmyadmin', '/config',
        '/config.php', '/.env', '/.git', '/backup',
        '/db', '/database', '/setup', '/install',
        '/shell', '/cmd', '/exec', '/eval',
        '/api/users', '/api/debug', '/api/test',
        '/swagger', '/api-docs', '/graphql'
    ]

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _sqlite_abs_uri('instaloop_dev.db')

class ProductionConfig(Config):
    DEBUG = False
    # Force Supabase URL for production to avoid SQLite fallback
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://postgres.ynotajlmnxdrvelzxdyq:Darson2017%40%40@aws-1-us-east-1.pooler.supabase.com:6543/postgres'
    
    # Force production values if not set in environment
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or '967e561a954b541927ff56b1ca03237f9ca1abede1bf0d1d80b3d952054d181'
    ADMIN_ROUTE_SECRET = os.environ.get('ADMIN_ROUTE_SECRET') or 'Nj4SzW3JoQQ'
    SECRET_KEY = os.environ.get('SECRET_KEY') or '24ffbcb16d218148b229935b9019606ee345d8070bec2a6fa552046981520edf'
    
    # Debug log
    print(f"🔧 PRODUCTION CONFIG - DATABASE_URL: {SQLALCHEMY_DATABASE_URI[:50]}...")

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
