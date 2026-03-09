import hashlib
import json
import ipaddress
from flask import request
from utils.security import get_client_ip

def generate_fingerprint(request_obj=None) -> str:
    """
    Gera fingerprint multi-sinal do cliente usando múltiplos headers e IP.
    Não confia apenas em IP para evitar bypass via VPN/proxy.
    """
    if request_obj is None:
        request_obj = request
    
    # Coleta de múltiplos sinais
    fingerprint_data = {
        # Headers básicos
        "user_agent": request_obj.headers.get("User-Agent", "")[:500],  # Limitar tamanho
        
        # Headers de aceitação
        "accept_language": request_obj.headers.get("Accept-Language", "")[:100],
        "accept_encoding": request_obj.headers.get("Accept-Encoding", "")[:100],
        "accept": request_obj.headers.get("Accept", "")[:200],
        
        # Headers modernos de browser
        "sec_ch_ua": request_obj.headers.get("Sec-CH-UA", "")[:200],
        "sec_ch_platform": request_obj.headers.get("Sec-CH-Platform", "")[:100],
        "sec_ch_ua_mobile": request_obj.headers.get("Sec-CH-UA-Mobile", "")[:20],
        "sec_ch_ua_arch": request_obj.headers.get("Sec-CH-UA-Arch", "")[:100],
        "sec_ch_ua_bitness": request_obj.headers.get("Sec-CH-UA-Bitness", "")[:100],
        "sec_ch_ua_full_version": request_obj.headers.get("Sec-CH-UA-Full-Version", "")[:100],
        
        # Headers de segurança
        "sec_fetch_site": request_obj.headers.get("Sec-Fetch-Site", "")[:50],
        "sec_fetch_mode": request_obj.headers.get("Sec-Fetch-Mode", "")[:50],
        "sec_fetch_dest": request_obj.headers.get("Sec-Fetch-Dest", "")[:50],
        "sec_fetch_user": request_obj.headers.get("Sec-Fetch-User", "")[:50],
        
        # Headers adicionais
        "dnt": request_obj.headers.get("DNT", "")[:10],  # Do Not Track
        "upgrade_insecure_requests": request_obj.headers.get("Upgrade-Insecure-Requests", "")[:10],
        "save_data": request_obj.headers.get("Save-Data", "")[:10],
        
        # IP information (subnet para evitar mudanças de IP dinâmico)
        "ip_subnet": get_ip_subnet(get_client_ip(request_obj)),
        
        # Informações de conexão (se disponíveis)
        "x_forwarded_for": request_obj.headers.get("X-Forwarded-For", "")[:200],
        "x_real_ip": request_obj.headers.get("X-Real-IP", "")[:50],
        "cf_connecting_ip": request_obj.headers.get("CF-Connecting-IP", "")[:50],  # Cloudflare
        
        # Headers de cache
        "cache_control": request_obj.headers.get("Cache-Control", "")[:100],
        "pragma": request_obj.headers.get("Pragma", "")[:100],
        
        # Headers específicos
        "origin": request_obj.headers.get("Origin", "")[:200],
        "referer": request_obj.headers.get("Referer", "")[:200],
    }
    
    # Remover valores vazios para consistência
    fingerprint_data = {k: v for k, v in fingerprint_data.items() if v}
    
    # Ordenar chaves para garantir consistência
    fingerprint_json = json.dumps(fingerprint_data, sort_keys=True, separators=(',', ':'))
    
    # Gerar hash SHA-256
    fingerprint_hash = hashlib.sha256(fingerprint_json.encode('utf-8')).hexdigest()
    
    return fingerprint_hash

def get_ip_subnet(ip_address: str) -> str:
    """
    Extrai subnet do IP (primeiros 3 octetos para IPv4, /64 para IPv6).
    Isso permite alguma variação de IP sem mudar completamente o fingerprint.
    """
    try:
        ip = ipaddress.ip_address(ip_address)
        
        if ip.version == 4:
            # Para IPv4, usar /24 (primeiros 3 octetos)
            network = ipaddress.ip_network(f"{ip}/24", strict=False)
            return str(network.network_address)
        else:
            # Para IPv6, usar /64
            network = ipaddress.ip_network(f"{ip}/64", strict=False)
            return str(network.network_address)
            
    except (ValueError, TypeError):
        # Se IP for inválido, retornar valor padrão
        return "0.0.0.0"

def is_ip_in_private_range(ip_address: str) -> bool:
    """
    Verifica se IP está em range privado (RFC 1918, RFC 4193).
    """
    try:
        ip = ipaddress.ip_address(ip_address)
        
        # Ranges privados IPv4
        private_ranges_v4 = [
            ipaddress.ip_network('10.0.0.0/8'),
            ipaddress.ip_network('172.16.0.0/12'),
            ipaddress.ip_network('192.168.0.0/16'),
            ipaddress.ip_network('127.0.0.0/8'),  # Loopback
            ipaddress.ip_network('169.254.0.0/16'),  # Link-local
        ]
        
        # Ranges privados IPv6
        private_ranges_v6 = [
            ipaddress.ip_network('::1/128'),  # Loopback
            ipaddress.ip_network('fc00::/7'),  # Unique local
            ipaddress.ip_network('fe80::/10'),  # Link-local
        ]
        
        private_ranges = private_ranges_v4 if ip.version == 4 else private_ranges_v6
        
        return any(ip in network for network in private_ranges)
        
    except (ValueError, TypeError):
        return False

def get_fingerprint_similarity(fp1: str, fp2: str) -> float:
    """
    Calcula similaridade entre dois fingerprints.
    Retorna valor entre 0.0 e 1.0.
    """
    if fp1 == fp2:
        return 1.0
    
    # Se forem completamente diferentes
    if not fp1 or not fp2:
        return 0.0
    
    # Para implementação futura: poderia analisar componentes individuais
    # Por enquanto, retorna 0 ou 1
    return 0.0

def is_suspicious_fingerprint_change(old_fp: str, new_fp: str, threshold: float = 0.8) -> bool:
    """
    Verifica se mudança de fingerprint é suspeita.
    """
    if not old_fp or not new_fp:
        return True
    
    similarity = get_fingerprint_similarity(old_fp, new_fp)
    return similarity < threshold

def extract_browser_info(fingerprint_data: dict) -> dict:
    """
    Extrai informações do browser dos dados do fingerprint.
    """
    user_agent = fingerprint_data.get("user_agent", "")
    sec_ch_ua = fingerprint_data.get("sec_ch_ua", "")
    
    browser_info = {
        "user_agent": user_agent,
        "likely_browser": "unknown",
        "likely_os": "unknown",
        "is_mobile": False,
        "is_bot": False
    }
    
    # Análise básica de User-Agent
    ua_lower = user_agent.lower()
    
    # Detectar browsers
    if "chrome" in ua_lower and "edg" not in ua_lower:
        browser_info["likely_browser"] = "chrome"
    elif "firefox" in ua_lower:
        browser_info["likely_browser"] = "firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser_info["likely_browser"] = "safari"
    elif "edg" in ua_lower:
        browser_info["likely_browser"] = "edge"
    elif "opera" in ua_lower or "opr" in ua_lower:
        browser_info["likely_browser"] = "opera"
    
    # Detectar OS
    if "windows" in ua_lower:
        browser_info["likely_os"] = "windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        browser_info["likely_os"] = "macos"
    elif "linux" in ua_lower:
        browser_info["likely_os"] = "linux"
    elif "android" in ua_lower:
        browser_info["likely_os"] = "android"
        browser_info["is_mobile"] = True
    elif "iphone" in ua_lower or "ipad" in ua_lower or "ios" in ua_lower:
        browser_info["likely_os"] = "ios"
        browser_info["is_mobile"] = True
    
    # Detectar móvel via headers
    sec_ch_ua_mobile = fingerprint_data.get("sec_ch_ua_mobile", "")
    if sec_ch_ua_mobile == "?1":
        browser_info["is_mobile"] = True
    
    # Detectar bots
    bot_patterns = [
        "bot", "crawler", "spider", "scraper", "curl", "wget",
        "python", "java", "node", "go-http", "rust"
    ]
    
    if any(pattern in ua_lower for pattern in bot_patterns):
        browser_info["is_bot"] = True
    
    return browser_info

def validate_fingerprint_consistency(request_obj, stored_fingerprint: str) -> tuple[bool, str]:
    """
    Valida consistência do fingerprint com request atual.
    Retorna (is_valid, reason).
    """
    current_fingerprint = generate_fingerprint(request_obj)
    
    if not stored_fingerprint:
        return True, "no_stored_fingerprint"
    
    if current_fingerprint == stored_fingerprint:
        return True, "match"
    
    # Análise de mudança
    similarity = get_fingerprint_similarity(current_fingerprint, stored_fingerprint)
    
    if similarity < 0.5:
        return False, "significant_change"
    
    return True, "minor_change"

def create_fingerprint_key(user_id: str, purpose: str = "general") -> str:
    """
    Cria chave para armazenamento de fingerprint em cache.
    """
    return f"fingerprint:{user_id}:{purpose}"
