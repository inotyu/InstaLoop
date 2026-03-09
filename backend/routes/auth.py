from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt
)
from sqlalchemy import or_, func
import pyotp
import secrets

from models import User, RefreshToken, PasswordReset
from extensions import db
from utils.security import (
    hash_password, verify_password, timing_safe_compare,
    generate_secure_token, hash_token, verify_token,
    generate_totp_secret, verify_totp, get_totp_provisioning_uri,
    validate_email, validate_password_strength
)
from utils.validators import validate_endpoint_fields, ValidationError
from utils.fingerprint import generate_fingerprint
from utils.audit import log_auth_event, log_security_event
from utils.behavioral import detect_automated_behavior, ban_user_if_bot
from extensions import limiter

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def _register_rate_limit():
    # Em desenvolvimento, permitir mais tentativas para testes.
    # Em produção, manter o limite estrito definido na spec.
    return "30 per hour" if current_app.debug else "3 per hour"

# Rate limiting por endpoint
@auth_bp.before_request
def check_rate_limit():
    """Verifica rate limiting baseado em IP + fingerprint"""
    ip = request.remote_addr
    fingerprint = generate_fingerprint(request)
    
    # Combinar IP e fingerprint para rate limiting
    key = f"rate_limit:{ip}:{fingerprint}"
    
    # Detectar comportamento automatizado
    # Em desenvolvimento, não bloquear via behavioral para não atrapalhar testes locais.
    if not current_app.debug:
        detection_result = detect_automated_behavior()
        if detection_result['should_block']:
            log_security_event('rate_limit_exceeded')
            return jsonify({"error": "Muitas tentativas. Tente novamente mais tarde."}), 429

@auth_bp.route('/register', methods=['POST'])
@limiter.limit(_register_rate_limit)
def register():
    """
    Registro de novo usuário com validações de segurança.
    """
    try:
        # Validar e filtrar campos
        data, errors = validate_endpoint_fields('auth_register', request.get_json())
        if errors:
            log_security_event('register_failed', details={'validation_errors': errors})
            return jsonify({"error": "Dados inválidos", "details": errors}), 400
        
        email = data['email']
        username = data['username']
        password = data['password']
        
        # Verificar se usuário já existe
        existing_user = User.query.filter(
            or_(User.email == email, User.username == username)
        ).first()
        
        if existing_user:
            # Timing-safe: não revelar se é email ou username que existe
            log_auth_event('register_failed', resultado='user_exists')
            return jsonify({"error": "Email ou username já está em uso"}), 400
        
        # Validar força da senha
        is_strong, strength_errors = validate_password_strength(password)
        if not is_strong:
            log_security_event('register_failed', details={'weak_password': strength_errors})
            return jsonify({"error": "Senha muito fraca", "details": strength_errors}), 400
        
        # Criar novo usuário
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password)
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Gerar 2FA se for admin (em produção, admin seria criado por outro processo)
        if username == 'admin':
            user.is_admin = True
            user.totp_secret = generate_totp_secret()
            db.session.commit()
            
            provisioning_uri = get_totp_provisioning_uri(email, user.totp_secret)
            log_auth_event('2fa_enabled', user_id=str(user.id))
        else:
            provisioning_uri = None
        
        # Log de sucesso
        log_auth_event('register_success', user_id=str(user.id))
        
        response_data = {
            "message": "Usuário criado com sucesso",
            "user_id": str(user.id),
            "username": user.username
        }
        
        if provisioning_uri:
            response_data["totp_setup_uri"] = provisioning_uri
        
        return jsonify(response_data), 201
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("register_error")
        try:
            log_security_event('register_failed', details={'error': str(e)})
        except Exception:
            pass
        return jsonify({"error": "Erro interno do servidor"}), 500

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Login de usuário com suporte a email/username e senha"""
    try:
        print("=" * 50)
        print(f"🔐 LOGIN REQUEST RECEBIDO - {datetime.utcnow()}")
        print(f"📋 Headers: {dict(request.headers)}")
        print(f"📋 Method: {request.method}")
        print(f"📋 Content-Type: {request.content_type}")
        print("=" * 50)

        raw_json = request.get_json()
        print(f'RAW JSON: {raw_json}')

        data, errors = validate_endpoint_fields('auth_login', raw_json, raw_json)
        if errors:
            print(f'VALIDATION ERRORS: {errors}')
            log_security_event('login_failed', details={'validation_errors': errors})
            return jsonify({"error": "Credenciais inválidas"}), 400

        identifier = data.get('identifier')
        password = data.get('password')

        print(f'🔍 Dados extraídos: identifier={identifier}, password_present={bool(password)}')

        # Normalizar email/username para busca case-insensitive
        identifier = (identifier or "").strip().lower()

        # Buscar usuário por email OU username (case-insensitive)
        # Sempre faz a busca, mesmo que não exista, para mitigar timing attacks
        user = User.query.filter(
            or_(
                func.lower(User.email) == identifier,
                func.lower(User.username) == identifier,
            )
        ).first()

        # Debug
        print(f'Login attempt - Identifier: {identifier}, User found: {user is not None}')
        if user:
            print(f'User: {user.username}, Email: {user.email}, Admin: {user.is_admin}, Banned: {user.is_banned}')

        # Bootstrap de admin em ambiente de desenvolvimento:
        # Se não encontrou usuário mas estiver usando o email/username padrão do admin,
        # cria o usuário admin diretamente no banco usando as credenciais fornecidas.
        if not user and current_app.debug and identifier in ["admin@instaloop.com", "admin"]:
            print("⚠️ Bootstrap admin: usuário não encontrado, criando admin de desenvolvimento...")
            user = User(
                username="admin",
                email="admin@instaloop.com",
                password_hash=hash_password(password),
                is_admin=True,
                is_private=False,
                bio="Administrador do sistema (bootstrap dev)"
            )
            db.session.add(user)
            db.session.commit()
            print(f'Bootstrap admin criado com ID: {user.id}')

        # Verificar se usuário está bloqueado
        if user and user.is_banned:
            log_auth_event('login_failed', user_id=str(user.id), resultado='user_banned')
            return jsonify({"error": "Credenciais inválidas"}), 400

        # Verificar lockout por tentativas
        if user and user.locked_until and user.locked_until > datetime.utcnow():
            log_auth_event('login_locked', user_id=str(user.id))
            return jsonify({"error": "Credenciais inválidas"}), 400

        # Verificar senha (timing-safe)
        password_valid = False
        if user:
            password_valid = verify_password(password, user.password_hash)
            print(f'Password check: {password_valid}')

        if not user or not password_valid:
            # Incrementar tentativas falhas
            if user:
                user.failed_login_attempts += 1

                # Lockout progressivo
                if user.failed_login_attempts >= 5:
                    lockout_duration = timedelta(minutes=15)  # Primeiro lockout: 15min
                    if user.failed_login_attempts >= 10:
                        lockout_duration = timedelta(hours=1)   # Segundo: 1h
                    if user.failed_login_attempts >= 15:
                        lockout_duration = timedelta(hours=24)  # Terceiro: 24h

                    user.locked_until = datetime.utcnow() + lockout_duration

                db.session.commit()

            log_auth_event('login_failed', user_id=str(user.id) if user else None, resultado='invalid_credentials')
            return jsonify({"error": "Credenciais inválidas"}), 400

        # Resetar tentativas falhas
        user.failed_login_attempts = 0
        user.locked_until = None

        # 2FA não é mais exigido no login - apenas no acesso ao painel admin
        # Para admin, apenas logar que tem 2FA configurado (para verificação posterior)
        if user.is_admin and user.totp_secret:
            log_auth_event('admin_login_2fa_configured', user_id=str(user.id))

        # Gerar tokens JWT
        access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'username': user.username,
                'is_admin': user.is_admin,
                'fingerprint': generate_fingerprint(request)
            }
        )

        refresh_token = create_refresh_token(identity=str(user.id))

        # Armazenar refresh token no banco (hash apenas)
        refresh_token_hash = hash_token(refresh_token)
        token_entry = RefreshToken(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        )

        db.session.add(token_entry)
        db.session.commit()

        # Log de sucesso
        log_auth_event('login_success', user_id=str(user.id))

        # Setar refresh token em cookie HttpOnly
        response = jsonify({
            "access_token": access_token,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_private": user.is_private,
                "avatar_url": user.avatar_url,
                "bio": user.bio
            }
        })

        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=not current_app.debug,
            samesite='Lax' if current_app.debug else 'Strict',
            max_age=int(current_app.config['JWT_REFRESH_TOKEN_EXPIRES'].total_seconds())
        )

        return response

    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        print(f'LOGIN ERROR: {str(e)}')
        import traceback
        traceback.print_exc()
        db.session.rollback()
        log_security_event('login_failed', details={'error': str(e)})
        return jsonify({"error": "Erro interno do servidor"}), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Renova access token usando refresh token.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar se refresh token é válido
        refresh_token = request.cookies.get('refresh_token')
        if not refresh_token:
            log_security_event('jwt_invalid', user_id=current_user_id)
            return jsonify({"error": "Refresh token não encontrado"}), 401
        
        # Buscar token no banco
        token_hash = hash_token(refresh_token)
        token_entry = RefreshToken.query.filter_by(
            token_hash=token_hash,
            revoked=False
        ).first()
        
        if not token_entry or token_entry.expires_at < datetime.utcnow():
            log_security_event('jwt_expired', user_id=current_user_id)
            return jsonify({"error": "Refresh token inválido ou expirado"}), 401
        
        # Verificar fingerprint
        current_fingerprint = generate_fingerprint(request)
        stored_fingerprint = get_jwt().get('fingerprint')
        
        if stored_fingerprint and current_fingerprint != stored_fingerprint:
            log_security_event('suspicious_activity', user_id=current_user_id, 
                             details={'fingerprint_mismatch': True})
            return jsonify({"error": "Sessão inválida"}), 401
        
        # Gerar novo access token
        user = User.query.get(current_user_id)
        if not user or user.is_banned:
            log_security_event('jwt_invalid', user_id=current_user_id)
            return jsonify({"error": "Usuário inválido"}), 401
        
        new_access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'username': user.username,
                'is_admin': user.is_admin,
                'fingerprint': current_fingerprint
            }
        )
        
        # Gerar novo refresh token (session fixation protection)
        new_refresh_token = create_refresh_token(identity=str(user.id))
        
        # Revogar token antigo
        token_entry.revoked = True
        
        # Criar novo token entry
        new_token_hash = hash_token(new_refresh_token)
        new_token_entry = RefreshToken(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
        )
        
        db.session.add(new_token_entry)
        db.session.commit()
        
        response = jsonify({"access_token": new_access_token})
        
        response.set_cookie(
            'refresh_token',
            new_refresh_token,
            httponly=True,
            secure=not current_app.debug,
            samesite='Lax' if current_app.debug else 'Strict',
            max_age=int(current_app.config['JWT_REFRESH_TOKEN_EXPIRES'].total_seconds())
        )
        
        return response
        
    except Exception as e:
        log_security_event('jwt_invalid', details={'error': str(e)})
        return jsonify({"error": "Erro ao renovar token"}), 401

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout revogando refresh token.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Revogar todos os refresh tokens do usuário
        refresh_token = request.cookies.get('refresh_token')
        if refresh_token:
            token_hash = hash_token(refresh_token)
            token_entry = RefreshToken.query.filter_by(token_hash=token_hash).first()
            if token_entry:
                token_entry.revoked = True
                db.session.commit()
        
        log_auth_event('logout', user_id=current_user_id)
        
        # Limpar cookie
        response = jsonify({"message": "Logout realizado com sucesso"})
        response.delete_cookie('refresh_token')
        
        return response
        
    except Exception as e:
        log_security_event('logout_failed', user_id=get_jwt_identity(), details={'error': str(e)})
        return jsonify({"error": "Erro ao fazer logout"}), 500

@auth_bp.route('/reset-password', methods=['POST'])
@limiter.limit("3 per hour")
def reset_password():
    """
    Solicitação de reset de senha.
    """
    try:
        data, errors = validate_endpoint_fields('auth_reset_password', request.get_json())
        if errors:
            return jsonify({"error": "Dados inválidos"}), 400
        
        email = data['email']
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({"error": "Email não encontrado"}), 404
        
        # Gerar token de reset
        token = secrets.token_urlsafe(32)
        token_hash = generate_secure_token(token)
        
        # Salvar token no banco
        reset = PasswordReset(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(reset)
        db.session.commit()
        
        # TODO: Enviar email com token
        
        log_auth_event('password_reset_requested', user.id, success=True)
        
        return jsonify({"message": "Email de reset enviado"}), 200
        
    except Exception as e:
        log_security_event('password_reset_error', details={'error': str(e)})
        return jsonify({"error": "Erro ao solicitar reset"}), 500

@auth_bp.route('/confirm-reset', methods=['POST'])
@limiter.limit("5 per hour")
def confirm_password_reset():
    """
    Confirmação de reset de senha com token.
    """
    try:
        data, errors = validate_endpoint_fields('auth_confirm_reset', request.get_json())
        if errors:
            return jsonify({"error": "Dados inválidos"}), 400
        
        token = data['token']
        new_password = data['new_password']
        
        # Validar força da nova senha
        is_strong, strength_errors = validate_password_strength(new_password)
        if not is_strong:
            return jsonify({"error": "Senha muito fraca", "details": strength_errors}), 400
        
        # Verificar token
        token_hash = hash_token(token)
        reset_entry = PasswordReset.query.filter_by(
            token_hash=token_hash,
            used=False
        ).first()
        
        if not reset_entry or reset_entry.expires_at < datetime.utcnow():
            log_security_event('password_reset_failed', details={'invalid_token': True})
            return jsonify({"error": "Token inválido ou expirado"}), 400
        
        user = User.query.get(reset_entry.user_id)
        if not user or user.is_banned:
            return jsonify({"error": "Solicitação inválida"}), 400
        
        # Atualizar senha
        user.password_hash = hash_password(new_password)
        user.failed_login_attempts = 0  # Resetar tentativas falhas
        user.locked_until = None
        
        # Marcar token como usado
        reset_entry.used = True
        
        db.session.commit()
        
        log_auth_event('password_reset_success', user_id=str(user.id))
        
        return jsonify({"message": "Senha alterada com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        log_security_event('password_reset_failed', details={'error': str(e)})
        return jsonify({"error": "Erro interno do servidor"}), 500

@auth_bp.route('/verify-2fa', methods=['POST'])
@jwt_required()
def verify_2fa():
    """
    Verificação de código 2FA TOTP.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_admin or not user.totp_secret:
            return jsonify({"error": "2FA não configurado"}), 400
        
        data, errors = validate_endpoint_fields('auth_2fa_verify', request.get_json())
        if errors:
            return jsonify({"error": "Dados inválidos"}), 400
        
        totp_code = data['totp_code']
        
        if verify_totp(totp_code, user.totp_secret):
            log_auth_event('2fa_verify_success', user_id=current_user_id)
            return jsonify({"message": "2FA verificado com sucesso"})
        else:
            log_auth_event('2fa_verify_failed', user_id=current_user_id)
            return jsonify({"error": "Código 2FA inválido"}), 400
        
    except Exception as e:
        log_security_event('2fa_verify_failed', user_id=get_jwt_identity(), details={'error': str(e)})
        return jsonify({"error": "Erro ao verificar 2FA"}), 500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Retorna informações do usuário atual.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.is_banned:
            log_security_event('jwt_invalid', user_id=current_user_id)
            return jsonify({"error": "Usuário inválido"}), 401
        
        return jsonify({
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "is_private": user.is_private,
            "is_admin": user.is_admin,
            "created_at": user.created_at.isoformat(),
            "followers_count": user.following.filter_by(status='accepted').count(),
            "following_count": user.followers.filter_by(status='accepted').count(),
            "posts_count": user.posts.count()
        })
        
    except Exception as e:
        return jsonify({"error": "Erro ao obter informações"}), 500

@auth_bp.route('/reset-password-request', methods=['POST'])
@limiter.limit("30 per hour")  # Aumentado para testes
def reset_password_request():
    """
    Solicita reset de senha via email.
    Sempre retorna mensagem genérica para não revelar se email existe.
    """
    try:
        data = request.get_json()
        if not data or not data.get('email'):
            return jsonify({"message": "Se o email existir, você receberá as instruções."}), 200
        
        email = data['email'].strip().lower()
        
        # Validar formato do email
        if not validate_email(email):
            return jsonify({"message": "Se o email existir, você receberá as instruções."}), 200
        
        # Buscar usuário (não revelar se existe ou não)
        user = User.query.filter_by(email=email).first()
        
        if user and not user.is_banned:
            # Verificar se já existe token não usado
            from models import PasswordReset
            from datetime import datetime, timedelta
            import hashlib
            import secrets
            
            # Invalidar tokens antigos
            PasswordReset.query.filter_by(
                user_id=user.id,
                used=False
            ).update({'used': True})
            db.session.commit()
            
            # Gerar novo token
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            # Salvar no banco
            reset = PasswordReset(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(minutes=15),
                used=False
            )
            db.session.add(reset)
            db.session.commit()
            
            # Enviar email
            from utils.email_service import email_service
            email_sent = email_service.send_reset_email(email, token)
            
            if email_sent:
                print(f"Password reset email sent to: {email[:10]}***")
            else:
                print(f"Password reset email failed to: {email[:10]}***")
        
        # Sempre retornar mensagem genérica
        return jsonify({"message": "Se o email existir, você receberá as instruções."}), 200
        
    except Exception as e:
        print(f"Password reset request error: {str(e)}")
        # Sempre retornar mensagem genérica mesmo em erro
        return jsonify({"message": "Se o email existir, você receberá as instruções."}), 200

@auth_bp.route('/reset-password-confirm', methods=['POST'])
@limiter.limit("30 per hour")  # Aumentado para testes
def reset_password_confirm():
    """
    Confirma reset de senha com token.
    """
    try:
        data = request.get_json()
        if not data or not data.get('token') or not data.get('new_password'):
            return jsonify({"error": "Token e nova senha são obrigatórios"}), 400
        
        token = data['token']
        new_password = data['new_password']
        
        # Validar força da senha
        if not validate_password_strength(new_password):
            return jsonify({"error": "Senha muito fraca. Use pelo menos 8 caracteres com letras, números e símbolos"}), 400
        
        # Hash do token
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Buscar token válido
        from models import PasswordReset
        reset = PasswordReset.query.filter_by(
            token_hash=token_hash,
            used=False
        ).first()
        
        if not reset:
            log_security_event('password_reset_invalid_token', details={'token_hash': token_hash[:16] + '***'})
            return jsonify({"error": "Token inválido ou expirado"}), 400
        
        # Verificar expiração
        if datetime.utcnow() > reset.expires_at:
            log_security_event('password_reset_expired', user_id=reset.user_id)
            return jsonify({"error": "Token expirado"}), 400
        
        # Buscar usuário
        user = User.query.get(reset.user_id)
        if not user or user.is_banned:
            return jsonify({"error": "Token inválido"}), 400
        
        # Atualizar senha
        print(f"🔄 PASSWORD RESET - User: {user.username}")
        print(f"🔄 Old hash length: {len(user.password_hash)}")
        
        user.password_hash = hash_password(new_password)
        print(f"🔄 New hash length: {len(user.password_hash)}")
        print(f"🔄 New password: {new_password}")
        
        user.failed_login_attempts = 0
        user.locked_until = None
        
        # Marcar token como usado
        reset.used = True
        
        # Invalidar todos os refresh tokens do usuário
        from models import RefreshToken
        RefreshToken.query.filter_by(user_id=user.id).update({'revoked': True})
        
        db.session.commit()
        
        print(f"Password reset completed for user: {user.id}")
        
        return jsonify({"message": "Senha redefinida com sucesso"}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Password reset confirm error: {str(e)}")
        return jsonify({"error": "Erro ao redefinir senha"}), 500
