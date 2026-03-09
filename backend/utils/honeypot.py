import json
import random
from datetime import datetime
from flask import request, jsonify
from utils.security import get_client_ip
from utils.fingerprint import generate_fingerprint
from models import HoneypotLog
from extensions import db

# Respostas falsas para confundir atacantes
HONEYPOT_RESPONSES = [
    {"status": "ok", "data": []},
    {"success": True, "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"},
    {"users": [], "total": 0, "page": 1},
    {"message": "Carregando...", "progress": 23},
    {"result": "success", "count": 0},
    {"data": {"items": [], "has_more": False}},
    {"response": "authenticated", "session_id": "sess_12345"},
    {"status": "ready", "version": "1.0.0"},
]

# Rotas honeypot configuradas
HONEYPOT_ROUTES = [
    '/admin',
    '/dashboard', 
    '/cms',
    '/painel',
    '/wp-admin',
    '/wp-login.php',
    '/administrator',
    '/login-admin',
    '/api/admin',
    '/api/v1/admin',
    '/api/v2/admin',
    '/phpmyadmin',
    '/config',
    '/config.php',
    '/.env',
    '/.git',
    '/backup',
    '/db',
    '/database',
    '/setup',
    '/install',
    '/shell',
    '/cmd',
    '/exec',
    '/eval',
    '/api/users',  # Sem auth - retorna lista falsa
    '/api/debug',
    '/api/test',
    '/swagger',
    '/api-docs',
    '/graphql',
    '/console',
    '/logs',
    '/tmp',
    '/temp',
    '/cache',
    '/storage',
    '/uploads/raw',
    '/.well-known',
    '/robots.txt',
    '/sitemap.xml',
    '/crossdomain.xml',
    '/manifest.json',
    '/favicon.ico',
]

def is_honeypot_route(path: str) -> bool:
    """
    Verifica se a rota é um honeypot.
    """
    # Normalizar path
    path = path.lower().rstrip('/')
    
    # Verificar match exato
    if path in [route.lower().rstrip('/') for route in HONEYPOT_ROUTES]:
        return True
    
    # Verificar se contém padrões suspeitos
    suspicious_patterns = [
        'admin', 'config', 'debug', 'test', 'setup', 'install',
        'shell', 'cmd', 'exec', 'eval', 'backup', 'database',
        'logs', 'tmp', 'temp', 'cache', 'storage'
    ]
    
    # Exceções legítimas que contêm padrões suspeitos
    legitimate_exceptions = [
        '/api/auth/verify-admin',
        '/api/audit/admin-access',
        '/api/posts', 
        '/api/users/profile',
        '/admin123',
        '/admin123/verify-2fa',
        '/admin123/dashboard'
    ]
    
    if path in legitimate_exceptions:
        return False
    
    for pattern in suspicious_patterns:
        if pattern in path:
            return True
    
    return False

def log_honeypot_access(event_type: str = "route_access", additional_data: dict = None):
    """
    Registra acesso ao honeypot de forma silenciosa.
    """
    try:
        # Coletar informações do request
        ip_address = get_client_ip(request)
        fingerprint = generate_fingerprint(request)
        user_agent = request.headers.get('User-Agent', '')
        
        # Coletar headers completos (limitar para evitar logs muito grandes)
        headers = {}
        for key, value in request.headers.items():
            if key.lower().startswith(('x-', 'sec-', 'cf-')) or key.lower() in ['user-agent', 'referer', 'origin']:
                headers[key] = value[:500]  # Limitar tamanho
        
        # Coletar payload (limitar para evitar logs muito grandes)
        payload_preview = None
        if request.is_json:
            try:
                payload = request.get_json()
                payload_str = json.dumps(payload, separators=(',', ':'))
                payload_preview = payload_str[:1000]  # Primeiros 1000 chars
            except:
                payload_preview = "invalid_json"
        elif request.form:
            payload_preview = str(dict(request.form))[:1000]
        elif request.data:
            payload_preview = request.data.decode('utf-8', errors='ignore')[:1000]
        
        # Criar entrada no log
        honeypot_log = HoneypotLog(
            ip=ip_address,
            ip_subnet=extract_subnet(ip_address),
            fingerprint=fingerprint,
            user_agent=user_agent[:500],
            headers_json=headers,
            route=request.path,
            method=request.method,
            payload_preview=payload_preview,
            event_type=event_type,
            timestamp=datetime.utcnow()
        )
        
        # Adicionar dados adicionais se fornecidos
        if additional_data:
            if 'details' not in honeypot_log.headers_json:
                honeypot_log.headers_json['details'] = {}
            honeypot_log.headers_json['details'].update(additional_data)
        
        db.session.add(honeypot_log)
        db.session.commit()
        
    except Exception as e:
        # Silenciar erros para não revelar que é um honeypot
        db.session.rollback()
        pass

def get_fake_response() -> dict:
    """
    Retorna uma resposta falsa aleatória para confundir atacantes.
    """
    return random.choice(HONEYPOT_RESPONSES)

def create_honeypot_response(status_code: int = 200, content_type: str = 'application/json'):
    """
    Cria resposta HTTP falsa para honeypot.
    """
    response_data = get_fake_response()
    
    response = jsonify(response_data)
    response.status_code = status_code
    
    # Adicionar headers que parecem legítimos
    response.headers['Content-Type'] = content_type
    response.headers['Cache-Control'] = 'no-cache'
    
    # Às vezes adicionar delay para parecer processamento real
    if random.random() < 0.3:  # 30% de chance
        import time
        time.sleep(random.uniform(0.1, 0.5))
    
    return response

def extract_subnet(ip_address: str) -> str:
    """
    Extrai subnet do IP para agrupar acessos similares.
    """
    try:
        if '.' in ip_address:  # IPv4
            parts = ip_address.split('.')
            if len(parts) >= 3:
                return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        elif ':' in ip_address:  # IPv6
            parts = ip_address.split(':')
            if len(parts) >= 4:
                return f"{parts[0]}:{parts[1]}:{parts[2]}:{parts[3]}::/64"
    except:
        pass
    
    return ip_address

def detect_honeypot_patterns() -> dict:
    """
    Detecta padrões suspeitos no request atual.
    """
    patterns_detected = []
    
    # User-Agent suspeito
    user_agent = request.headers.get('User-Agent', '').lower()
    suspicious_agents = [
        'sqlmap', 'nikto', 'nmap', 'masscan', 'dirb', 'dirbuster',
        'gobuster', 'wfuzz', 'burp', 'owasp', 'zap', 'python-requests',
        'curl', 'wget', 'powershell', 'bash'
    ]
    
    for agent in suspicious_agents:
        if agent in user_agent:
            patterns_detected.append(f"suspicious_user_agent:{agent}")
    
    # Headers suspeitos
    for header_name, header_value in request.headers.items():
        header_lower = header_name.lower()
        value_lower = header_value.lower()
        
        # Headers de automação
        if any(pattern in header_lower for pattern in ['automation', 'bot', 'crawler']):
            patterns_detected.append(f"suspicious_header:{header_name}")
        
        # Valores suspeitos
        if any(pattern in value_lower for pattern in ['${', '{{', '<script', 'javascript:', 'eval(']):
            patterns_detected.append(f"suspicious_header_value:{header_name}")
    
    # Parâmetros suspeitos
    if request.args:
        for param_name, param_value in request.args.items():
            param_lower = param_name.lower()
            value_lower = param_value.lower()
            
            # Parâmetros de injeção
            if any(pattern in param_lower for pattern in ['id', 'file', 'page', 'debug', 'test']):
                patterns_detected.append(f"suspicious_param:{param_name}")
            
            # Valores de injeção
            if any(pattern in value_lower for pattern in ['union select', 'drop table', '<script', 'javascript:']):
                patterns_detected.append(f"injection_attempt:{param_name}")
    
    # Method suspeito
    if request.method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
        patterns_detected.append(f"suspicious_method:{request.method}")
    
    # Path traversal
    path = request.path.lower()
    if any(pattern in path for pattern in ['../', '..\\', '%2e%2e', 'etc/passwd', 'windows/system32']):
        patterns_detected.append("path_traversal_attempt")
    
    # SQL injection no path
    if any(pattern in path for pattern in ['union', 'select', 'drop', 'insert', 'update', 'delete']):
        patterns_detected.append("sql_injection_in_path")
    
    return {
        "patterns_detected": patterns_detected,
        "risk_score": len(patterns_detected) * 10,  # Score simples
        "is_high_risk": len(patterns_detected) >= 3
    }

def should_block_ip(ip_address: str) -> bool:
    """
    Verifica se IP deve ser bloqueado baseado em acessos anteriores.
    """
    try:
        # Contar acessos nas últimas 24h
        from datetime import timedelta
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        
        access_count = HoneypotLog.query.filter(
            HoneypotLog.ip == ip_address,
            HoneypotLog.timestamp > recent_cutoff
        ).count()
        
        # Bloquear se houver muitos acessos
        return access_count > 50
        
    except:
        return False

def get_honeypot_statistics() -> dict:
    """
    Retorna estatísticas dos acessos ao honeypot.
    """
    try:
        from datetime import timedelta
        
        # Últimas 24h
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_logs = HoneypotLog.query.filter(
            HoneypotLog.timestamp > recent_cutoff
        ).all()
        
        # Estatísticas básicas
        stats = {
            "last_24h": {
                "total_accesses": len(recent_logs),
                "unique_ips": len(set(log.ip for log in recent_logs)),
                "top_routes": {},
                "top_event_types": {},
                "high_risk_accesses": 0
            }
        }
        
        # Top rotas
        route_counts = {}
        for log in recent_logs:
            route = log.route
            route_counts[route] = route_counts.get(route, 0) + 1
        
        stats["last_24h"]["top_routes"] = dict(
            sorted(route_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        )
        
        # Top event types
        event_counts = {}
        for log in recent_logs:
            event = log.event_type or "unknown"
            event_counts[event] = event_counts.get(event, 0) + 1
        
        stats["last_24h"]["top_event_types"] = dict(
            sorted(event_counts.items(), key=lambda x: x[1], reverse=True)
        )
        
        # Acessos de alto risco
        for log in recent_logs:
            patterns = detect_honeypot_patterns()
            if patterns["is_high_risk"]:
                stats["last_24h"]["high_risk_accesses"] += 1
        
        return stats
        
    except Exception as e:
        return {"error": str(e)}

def handle_honeypot_request():
    """
    Handler principal para requests de honeypot.
    """
    # Detectar padrões
    patterns = detect_honeypot_patterns()
    
    # Log do acesso
    log_honeypot_access(
        event_type="route_access",
        additional_data={
            "risk_score": patterns["risk_score"],
            "patterns": patterns["patterns_detected"],
            "is_high_risk": patterns["is_high_risk"]
        }
    )
    
    # Verificar se deve bloquear
    ip_address = get_client_ip(request)
    if should_block_ip(ip_address):
        # Log de bloqueio
        log_honeypot_access(
            event_type="ip_blocked",
            additional_data={"reason": "too_many_accesses"}
        )
    
    # Retornar resposta falsa
    return create_honeypot_response()

def create_honeypot_route_handler(route_path: str):
    """
    Cria um handler específico para uma rota honeypot.
    """
    def handler():
        return handle_honeypot_request()
    
    handler.__name__ = f"honeypot_{route_path.replace('/', '_').replace('.', '_')}"
    return handler
