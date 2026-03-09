"""
Proteção contra Server-Side Request Forgery (SSRF).
"""
import ipaddress
import re
from urllib.parse import urlparse

# IPs privados bloqueados (RFC 1918, RFC 4193)
PRIVATE_IP_RANGES = [
    '127.0.0.0/8',     # Loopback
    '10.0.0.0/8',      # Private Class A
    '172.16.0.0/12',   # Private Class B
    '192.168.0.0/16',  # Private Class C
    '169.254.0.0/16',  # Link-local
    '::1/128',          # IPv6 loopback
    'fc00::/7',         # IPv6 unique local
    'fe80::/10',        # IPv6 link-local
]

# Domínios/metadados perigosos bloqueados
BLOCKED_DOMAINS = [
    'metadata.google.internal',
    '169.254.169.254',  # AWS metadata
    'metadata.azure.com',
    'metadata.service.consul',
    'localhost',
    '0.0.0.0',
]

def is_private_ip(ip_str: str) -> bool:
    """
    Verifica se IP está em range privado.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        for range_str in PRIVATE_IP_RANGES:
            if ip in ipaddress.ip_network(range_str):
                return True
        return False
    except ValueError:
        return False

def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Valida URL contra SSRF.
    
    Returns:
        tuple[bool, str]: (is_safe, reason)
    """
    if not url or not isinstance(url, str):
        return False, "URL inválida"
    
    # Remover espaços e normalizar
    url = url.strip()
    
    # Verificar scheme
    if not url.startswith(('http://', 'https://')):
        return False, "Apenas HTTP/HTTPS permitidos"
    
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL malformada"
    
    # Verificar domínios bloqueados
    hostname = parsed.hostname or ''
    for blocked in BLOCKED_DOMAINS:
        if blocked in hostname.lower():
            return False, f"Domínio bloqueado: {blocked}"
    
    # Verificar se hostname é IP privado
    if hostname and re.match(r'^\d+\.\d+\.\d+\.\d+$', hostname):
        if is_private_ip(hostname):
            return False, f"IP privado bloqueado: {hostname}"
    
    # Verificar portas perigosas
    dangerous_ports = [22, 23, 25, 53, 135, 139, 445, 1433, 1521, 2049, 3306, 3389, 5432, 5984, 6379, 8080, 9200, 27017]
    if parsed.port and parsed.port in dangerous_ports:
        return False, f"Porta perigosa: {parsed.port}"
    
    # Verificar redirecionamentos (@)
    if '@' in url:
        return False, "Redirecionamento não permitido"
    
    # Verificar file:// protocol
    if url.startswith('file://'):
        return False, "Protocolo file:// bloqueado"
    
    # Verificar comprimento excessivo (DoS)
    if len(url) > 2048:
        return False, "URL muito longa"
    
    return True, "URL segura"

def validate_url_safety(url: str) -> bool:
    """
    Valida URL de forma simples (lança exceção se insegura).
    """
    is_safe, reason = is_safe_url(url)
    if not is_safe:
        raise ValueError(f"URL insegura: {reason}")
    return True
