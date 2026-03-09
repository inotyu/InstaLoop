import re
import uuid
from typing import Dict, List, Any, Tuple, Optional
from flask import request
from utils.security import contains_malicious_patterns, sanitize_input, validate_email, validate_username

# Whitelist de campos permitidos por endpoint
FIELD_WHITELISTS = {
    # Auth endpoints
    'auth_register': {
        'username', 'email', 'password'
    },
    'auth_login': {
        'identifier', 'password', 'hasPassword', 'totp_code'
    },
    'auth_reset_password': {
        'email'
    },
    'auth_confirm_reset': {
        'token', 'new_password'
    },
    'auth_2fa_verify': {
        'totp_code'
    },
    
    # User profile endpoints
    'user_update_profile': {
        'bio', 'avatar_url', 'is_private'
    },
    'user_change_password': {
        'current_password', 'new_password'
    },
    'user_change_email': {
        'new_email', 'password'
    },
    
    # Posts endpoints
    'post_create': {
        'content', 'media_url'
    },
    'post_update': {
        'content', 'media_url'
    },
    
    # Comments endpoints
    'comment_create': {
        'content'
    },
    'comment_update': {
        'content'
    },
    
    # Messages endpoints
    'message_send': {
        'content', 'media_url'
    },
    
    # Reports endpoints
    'report_create': {
        'target_type', 'target_id', 'reason'
    },
    
    # Admin endpoints
    'admin_update_user': {
        'is_banned', 'is_admin', 'is_private'
    },
    'admin_review_report': {
        'status'
    }
}

# Tipos de dados esperados por campo
FIELD_TYPES = {
    'username': str,
    'email': str,
    'password': str,
    'hasPassword': bool,
    'current_password': str,
    'new_password': str,
    'new_email': str,
    'bio': str,
    'avatar_url': str,
    'is_private': bool,
    'is_banned': bool,
    'is_admin': bool,
    'content': str,
    'media_url': str,
    'totp_code': str,
    'token': str,
    'target_type': str,
    'target_id': str,
    'reason': str,
    'status': str
}

# Tamanhos máximos por campo
FIELD_MAX_LENGTHS = {
    'username': 30,
    'email': 255,
    'password': 128,
    'current_password': 128,
    'new_password': 128,
    'new_email': 255,
    'bio': 500,
    'avatar_url': 500,
    'content': 2000,
    'media_url': 500,
    'totp_code': 10,
    'token': 100,
    'target_type': 10,
    'target_id': 50,
    'reason': 500,
    'status': 20
}

# Valores permitidos para campos específicos
ALLOWED_VALUES = {
    'target_type': {'post', 'user'},
    'status': {'pending', 'reviewed', 'dismissed'},
    'is_private': {True, False, 0, 1, 'true', 'false', 'True', 'False'},
    'is_banned': {True, False, 0, 1, 'true', 'false', 'True', 'False'},
    'is_admin': {True, False, 0, 1, 'true', 'false', 'True', 'False'}
}

class ValidationError(Exception):
    """Exceção para erros de validação"""
    def __init__(self, message: str, field: str = None, error_code: str = None):
        self.message = message
        self.field = field
        self.error_code = error_code
        super().__init__(message)

def validate_field_name(field_name: str) -> bool:
    """
    Valida se nome do campo é seguro (não contém caracteres perigosos).
    """
    if not field_name:
        return False
    
    # Permitir apenas letras, números e underscores
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
    return bool(re.match(pattern, field_name))

def validate_field_type(field_name: str, value: Any) -> bool:
    """
    Valida tipo do campo.
    """
    expected_type = FIELD_TYPES.get(field_name, str)
    
    # Conversão para booleanos
    if expected_type == bool:
        if isinstance(value, bool):
            return True
        if isinstance(value, str):
            return value.lower() in {'true', 'false', '1', '0'}
        if isinstance(value, int):
            return value in {0, 1}
        return False
    
    # Para strings, verificar se é string ou pode ser convertido
    if expected_type == str:
        return isinstance(value, (str, int, float, bool))
    
    return isinstance(value, expected_type)

def validate_field_length(field_name: str, value: str) -> bool:
    """
    Valida tamanho do campo.
    """
    if not isinstance(value, str):
        value = str(value)
    
    max_length = FIELD_MAX_LENGTHS.get(field_name)
    if max_length:
        return len(value) <= max_length
    
    return True

def validate_field_values(field_name: str, value: Any) -> bool:
    """
    Valida se valor está na lista de permitidos para campos específicos.
    """
    allowed = ALLOWED_VALUES.get(field_name)
    if not allowed:
        return True  # Campo não tem restrição de valores
    
    # Normalizar booleanos
    if isinstance(value, str):
        if value.lower() in {'true', '1'}:
            value = True
        elif value.lower() in {'false', '0'}:
            value = False
    
    return value in allowed

def validate_uuid_format(uuid_string: str) -> bool:
    """
    Valida formato de UUID v4.
    """
    try:
        uuid_obj = uuid.UUID(uuid_string)
        return str(uuid_obj) == uuid_string and uuid_obj.version == 4
    except (ValueError, AttributeError):
        return False

def validate_url_format(url: str) -> bool:
    """
    Valida formato básico de URL.
    """
    if not url:
        return True  # URL opcional
    
    pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    return bool(re.match(pattern, url))

def sanitize_field_value(field_name: str, value: Any) -> Any:
    """
    Sanitiza valor do campo conforme tipo.
    """
    if isinstance(value, str):
        # Sanitização contra XSS
        if field_name in ['content', 'bio', 'reason']:
            value = sanitize_input(value)
        
        # Trim de espaços
        value = value.strip()
        
        # Email em minúsculas
        if field_name == 'email':
            value = value.lower()
        
        # Username sem espaços
        if field_name == 'username':
            value = value.replace(' ', '_')
    
    # Conversão de booleanos
    if field_name in ['is_private', 'is_banned', 'is_admin']:
        if isinstance(value, str):
            if value.lower() in {'true', '1'}:
                value = True
            elif value.lower() in {'false', '0'}:
                value = False
        elif isinstance(value, int):
            value = bool(value)
    
    return value

def validate_endpoint_fields(endpoint_name: str, data: Dict[str, Any], raw_data: Dict[str, Any] = None) -> Tuple[Dict[str, Any], List[str]]:
    """
    Valida e filtra campos para um endpoint específico.
    Retorna (dados_filtrados, erros).
    """
    if not isinstance(data, dict):
        raise ValidationError("Dados devem ser um objeto JSON", error_code="invalid_data_type")
    
    # Verificar chaves duplicadas (parameter pollution)
    if raw_data and len(data) != len(raw_data):
        raise ValidationError("Chaves duplicadas detectadas", error_code="parameter_pollution")
    
    allowed_fields = FIELD_WHITELISTS.get(endpoint_name, set())
    filtered_data = {}
    errors = []
    
    for field_name, field_value in data.items():
        # 1. Validar nome do campo
        if not validate_field_name(field_name):
            errors.append(f"Campo '{field_name}' tem nome inválido")
            continue
        
        # 2. Verificar se campo está na whitelist
        if field_name not in allowed_fields:
            errors.append(f"Campo '{field_name}' não é permitido")
            continue
        
        # 3. Validar tipo
        if not validate_field_type(field_name, field_value):
            expected_type = FIELD_TYPES.get(field_name, str).__name__
            errors.append(f"Campo '{field_name}' deve ser do tipo {expected_type}")
            continue
        
        # 4. Sanitizar valor
        try:
            sanitized_value = sanitize_field_value(field_name, field_value)
        except Exception as e:
            errors.append(f"Erro ao sanitizar campo '{field_name}': {str(e)}")
            continue
        
        # 5. Validar tamanho
        if isinstance(sanitized_value, str) and not validate_field_length(field_name, sanitized_value):
            max_length = FIELD_MAX_LENGTHS.get(field_name, 'desconhecido')
            errors.append(f"Campo '{field_name}' excede tamanho máximo de {max_length} caracteres")
            continue
        
        # 6. Validar valores permitidos
        if not validate_field_values(field_name, sanitized_value):
            allowed = ALLOWED_VALUES.get(field_name, set())
            errors.append(f"Campo '{field_name}' deve ter um dos valores: {allowed}")
            continue
        
        # 7. Validações específicas por campo
        field_errors = validate_specific_field(field_name, sanitized_value)
        if field_errors:
            errors.extend(field_errors)
            continue
        
        # 8. Verificar padrões maliciosos
        if isinstance(sanitized_value, str) and contains_malicious_patterns(sanitized_value):
            errors.append(f"Campo '{field_name}' contém conteúdo suspeito")
            continue
        
        # Se passou por todas as validações, adicionar aos dados filtrados
        filtered_data[field_name] = sanitized_value
    
    return filtered_data, errors

def validate_specific_field(field_name: str, value: Any) -> List[str]:
    """
    Validações específicas para campos individuais.
    """
    errors = []
    
    if field_name == 'email' and isinstance(value, str):
        if not validate_email(value):
            errors.append("Email inválido")
    
    elif field_name == 'username' and isinstance(value, str):
        is_valid, validation_errors = validate_username(value)
        if not is_valid:
            errors.extend(validation_errors)
    
    elif field_name == 'password' and isinstance(value, str):
        is_valid, validation_errors = validate_password_strength(value)
        if not is_valid:
            errors.extend(validation_errors)
    
    elif field_name == 'new_password' and isinstance(value, str):
        is_valid, validation_errors = validate_password_strength(value)
        if not is_valid:
            errors.extend(validation_errors)
    
    elif field_name == 'totp_code' and isinstance(value, str):
        if not re.match(r'^\d{6}$', value):
            errors.append("Código TOTP deve ter 6 dígitos")
    
    elif field_name == 'target_id' and isinstance(value, str):
        if not validate_uuid_format(value):
            errors.append("ID de alvo deve ser um UUID válido")
    
    elif field_name in ['avatar_url', 'media_url'] and isinstance(value, str):
        if value and not validate_url_format(value):
            errors.append(f"URL inválida para campo '{field_name}'")
    
    return errors

def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    """
    Valida força da senha.
    """
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
    
    # Verificar senhas comuns
    common_passwords = [
        'password', '123456', '123456789', 'qwerty', 'abc123',
        'password123', 'admin', 'letmein', 'welcome', 'monkey'
    ]
    
    if password.lower() in common_passwords:
        errors.append("Senha muito comum, escolha uma mais segura")
    
    return len(errors) == 0, errors

def validate_query_params(params: Dict[str, Any], allowed_params: set) -> Tuple[Dict[str, Any], List[str]]:
    """
    Valida parâmetros de query string.
    """
    filtered_params = {}
    errors = []
    
    for param_name, param_value in params.items():
        if param_name not in allowed_params:
            errors.append(f"Parâmetro '{param_name}' não é permitido")
            continue
        
        # Sanitização básica
        if isinstance(param_value, str):
            param_value = sanitize_input(param_value)
        
        filtered_params[param_name] = param_value
    
    return filtered_params, errors

def validate_pagination_params(params: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Valida parâmetros de paginação.
    """
    allowed_params = {'page', 'limit', 'offset'}
    filtered_params, errors = validate_query_params(params, allowed_params)
    
    # Validações específicas de paginação
    if 'page' in filtered_params:
        try:
            page = int(filtered_params['page'])
            if page < 1:
                errors.append("Página deve ser maior que 0")
            elif page > 1000:
                errors.append("Página não pode ser maior que 1000")
            filtered_params['page'] = page
        except (ValueError, TypeError):
            errors.append("Página deve ser um número inteiro")
    
    if 'limit' in filtered_params:
        try:
            limit = int(filtered_params['limit'])
            if limit < 1:
                errors.append("Limite deve ser maior que 0")
            elif limit > 100:
                errors.append("Limite não pode ser maior que 100")
            filtered_params['limit'] = limit
        except (ValueError, TypeError):
            errors.append("Limite deve ser um número inteiro")
    
    if 'offset' in filtered_params:
        try:
            offset = int(filtered_params['offset'])
            if offset < 0:
                errors.append("Offset não pode ser negativo")
            elif offset > 10000:
                errors.append("Offset não pode ser maior que 10000")
            filtered_params['offset'] = offset
        except (ValueError, TypeError):
            errors.append("Offset deve ser um número inteiro")
    
    return filtered_params, errors
