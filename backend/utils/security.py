import hmac
import hashlib
import secrets
import pyotp
import bleach
import re
import argon2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2 import low_level
from flask import current_app, request

# Inicializa Argon2id com parâmetros configuráveis
def get_argon2_hasher():
    return PasswordHasher(
        time_cost=current_app.config.get('ARGON2_TIME_COST', 3),
        memory_cost=current_app.config.get('ARGON2_MEMORY_COST', 65536),
        parallelism=current_app.config.get('ARGON2_PARALLELISM', 2),
        hash_len=32,
        salt_len=16,
        type=low_level.Type.ID
    )

# Hash de senha com Argon2id
def hash_password(password: str) -> str:
    """Hash senha usando Argon2id com parâmetros configuráveis"""
    ph = get_argon2_hasher()
    return ph.hash(password)

# Verificação de senha com timing-safe comparison
def verify_password(password: str, password_hash: str) -> bool:
    """Verifica senha usando Argon2id com timing-safe comparison"""
    try:
        ph = get_argon2_hasher()
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        # Timing-safe: sempre faz o mesmo trabalho mesmo em caso de falha
        try:
            dummy_hash = ph.hash("dummy_password_for_timing")
            ph.verify(dummy_hash, "wrong_password")
        except Exception:
            pass
        return False
    except Exception:
        # Em caso de qualquer erro, retorna False de forma segura
        return False

# Timing-safe comparison para tokens e hashes
def timing_safe_compare(a: str, b: str) -> bool:
    """Compara duas strings de forma timing-safe"""
    return hmac.compare_digest(a.encode(), b.encode())

# Geração de token seguro
def generate_secure_token(length: int = 32) -> str:
    """Gera token URL-safe criptograficamente seguro"""
    return secrets.token_urlsafe(length)

# Hash de token para armazenamento (SHA-256)
def hash_token(token: str) -> str:
    """Hash token usando SHA-256 para armazenamento seguro"""
    return hashlib.sha256(token.encode()).hexdigest()

# Verificação de token com timing-safe compare
def verify_token(token: str, token_hash: str) -> bool:
    """Verifica token contra hash armazenado"""
    computed_hash = hash_token(token)
    return timing_safe_compare(computed_hash, token_hash)

# Geração de secret TOTP para 2FA
def generate_totp_secret() -> str:
    """Gera secret para TOTP (2FA)"""
    return pyotp.random_base32()

# Verificação TOTP
def verify_totp(token: str, secret: str) -> bool:
    """Verifica token TOTP"""
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Permite 1 janela de tempo
    except Exception:
        return False

# Geração de QR Code para TOTP (retorna URL para QR code)
def get_totp_provisioning_uri(email: str, secret: str) -> str:
    """Gera URI para QR code do TOTP"""
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name="InstaLoop"
    )

# Sanitização de inputs contra XSS
def sanitize_input(text: str) -> str:
    """Sanitiza texto contra XSS usando bleach"""
    if not text:
        return ""
    
    # Configuração bleach: permitir tags básicas, remover atributos perigosos
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'span']
    allowed_attributes = {'*': ['class']}
    
    return bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )

# Detecção de padrões maliciosos em inputs
def contains_malicious_patterns(text: str) -> bool:
    """Detecta padrões maliciosos comuns em inputs"""
    if not text:
        return False
    
    # Padrões perigosos (case-insensitive)
    malicious_patterns = [
        r'<script[^>]*>',
        r'javascript:',
        r'onerror\s*=',
        r'onload\s*=',
        r'eval\s*\(',
        r'document\.cookie',
        r'fetch\s*\(',
        r'XMLHttpRequest',
        r'--',
        r'/\*',
        r'DROP\s+TABLE',
        r'UNION\s+SELECT',
        r'\.\./',
        r'\.\.\\',
        r'<iframe',
        r'<object',
        r'<embed',
        r'<link',
        r'<meta',
        r'<style',
        r'@import',
        r'expression\s*\(',
        r'vbscript:',
        r'data:text/html',
    ]
    
    text_lower = text.lower()
    for pattern in malicious_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    
    return False

# Validação de força de senha
def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """Valida força da senha e retorna erros"""
    errors = []
    
    if len(password) < 8:
        errors.append("Senha deve ter pelo menos 8 caracteres")
    
    if len(password) > 128:
        errors.append("Senha deve ter no máximo 128 caracteres")
    
    if not re.search(r'[a-z]', password):
        errors.append("Senha deve conter pelo menos uma letra minúscula")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Senha deve conter pelo menos uma letra maiúscula")
    
    if not re.search(r'\d', password):
        errors.append("Senha deve conter pelo menos um número")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Senha deve conter pelo menos um caractere especial")
    
    # Verificar senhas comuns (lista básica)
    common_passwords = [
        'password', '123456', '123456789', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey'
    ]
    
    if password.lower() in common_passwords:
        errors.append("Senha muito comum, escolha uma mais segura")
    
    return len(errors) == 0, errors

# Geração de CSRF token
def generate_csrf_token() -> str:
    """Gera token CSRF seguro"""
    return generate_secure_token(32)

# Validação de CSRF token (double submit cookie pattern)
def validate_csrf_token(request_token: str, cookie_token: str) -> bool:
    """Valida token CSRF usando double submit cookie pattern"""
    if not request_token or not cookie_token:
        return False
    
    return timing_safe_compare(request_token, cookie_token)

# Validação de email
def validate_email(email: str) -> bool:
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Validação de username
def validate_username(username: str) -> tuple[bool, list[str]]:
    """Valida username e retorna erros"""
    errors = []
    
    if len(username) < 3:
        errors.append("Username deve ter pelo menos 3 caracteres")
    
    if len(username) > 30:
        errors.append("Username deve ter no máximo 30 caracteres")
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        errors.append("Username deve conter apenas letras, números e underscores")
    
    if username.startswith('_') or username.endswith('_'):
        errors.append("Username não pode começar ou terminar com underscore")
    
    if '__' in username:
        errors.append("Username não pode conter underscores consecutivos")
    
    return len(errors) == 0, errors

# Extração de IP seguro (considerando proxies)
def get_client_ip(request) -> str:
    """Extrai IP real do cliente considerando proxies"""
    # Headers comuns de proxy
    headers_to_check = [
        'X-Forwarded-For',
        'X-Real-IP',
        'X-Client-IP',
        'CF-Connecting-IP',  # Cloudflare
        'True-Client-IP',
    ]
    
    for header in headers_to_check:
        ip = request.headers.get(header)
        if ip:
            # X-Forwarded-For pode ter múltiplos IPs
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            
            # Validar formato IPv4/IPv6 básico
            if re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip) or ':' in ip:
                return ip
    
    # Fallback para IP direto
    return request.remote_addr or '0.0.0.0'

# Validação de Origin/Referer para CSRF
def validate_origin(request) -> bool:
    """Valida Origin/Referer headers contra whitelist"""
    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')
    
    # Em desenvolvimento, permitir localhost
    if current_app.debug:
        allowed_origins = ['http://localhost:3000', 'http://localhost:5173', 'http://localhost:5174']
    else:
        allowed_origins = current_app.config.get('CORS_ORIGINS', [])
    
    # Verificar Origin primeiro
    if origin:
        return origin in allowed_origins
    
    # Se não tem Origin, verificar Referer
    if referer:
        for allowed in allowed_origins:
            if referer.startswith(allowed):
                return True
    
    return False
