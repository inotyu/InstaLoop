from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token
from sqlalchemy import or_, and_, desc, func
from datetime import datetime, timedelta

from models import User, Post, Comment, Like, Message, Report, HoneypotLog, AuditLog
from extensions import db
from utils.validators import validate_endpoint_fields, ValidationError, validate_pagination_params
from utils.audit import log_admin_action, log_security_event
from utils.honeypot import get_honeypot_statistics
from utils.behavioral import get_user_behavior_profile
from utils.security import verify_totp
from extensions import limiter

# Blueprint com rota secreta via variável de ambiente
admin_bp = Blueprint('admin', __name__)

def verify_admin_access():
    """
    Verifica se usuário é admin com múltiplas camadas de segurança.
    """
    current_user_id = get_jwt_identity()
    
    # 1. Verificar se usuário existe
    user = User.query.get(current_user_id)
    if not user:
        log_security_event('admin_access_denied', user_id=current_user_id,
                         details={'reason': 'user_not_found'})
        abort(404)
    
    # 2. Verificar se é admin
    if not user.is_admin:
        log_security_event('admin_access_denied', user_id=current_user_id,
                         details={'reason': 'not_admin'})
        abort(404)
    
    # 3. Verificar se não está banido
    if user.is_banned:
        log_security_event('admin_access_denied', user_id=current_user_id,
                         details={'reason': 'user_banned'})
        abort(404)
    
    # 4. Verificar 2FA (se configurado) - agora exigido no acesso ao painel
    if user.totp_secret:
        # Verificar se 2FA foi verificado nesta sessão
        totp_verified = get_jwt().get('totp_verified', False)
        
        if not totp_verified:
            log_security_event('admin_2fa_required', user_id=current_user_id)
            abort(401)  # Mudar para abort em vez de retornar JSON
    else:
        log_security_event('admin_2fa_not_configured', user_id=current_user_id)
    
    # 5. Verificar fingerprint (session hijacking protection)
    current_fingerprint = get_jwt().get('fingerprint')
    if current_fingerprint:
        from utils.fingerprint import generate_fingerprint
        actual_fingerprint = generate_fingerprint(request)
        
        if current_fingerprint != actual_fingerprint:
            log_security_event('admin_session_hijack_attempt', user_id=current_user_id,
                             details={'expected_fp': current_fingerprint, 'actual_fp': actual_fingerprint})
            abort(404)
    
    return user

def get_admin_route(app):
    """Obtém rota admin secreta da config do app (sem depender de current_app)."""
    route = app.config.get('ADMIN_ROUTE_SECRET')
    if not route:
        raise RuntimeError("ADMIN_ROUTE_SECRET não configurado")

    return f"/{route}"

@admin_bp.route('/verify-2fa', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def admin_verify_2fa():
    """
    Verifica código TOTP para acesso ao painel admin.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Buscar usuário
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            return jsonify({"error": "Não autorizado"}), 401
        
        if not user.totp_secret:
            return jsonify({"error": "2FA não configurado"}), 400
        
        # Verificar código TOTP
        data = request.get_json()
        totp_code = data.get('totp_code')
        
        if not totp_code:
            return jsonify({"error": "Código TOTP requerido"}), 400
        
        import pyotp
        totp = pyotp.TOTP(user.totp_secret)
        
        if not verify_totp(totp_code, user.totp_secret):
            log_security_event('admin_2fa_verify_failed', user_id=current_user_id)
            return jsonify({"error": "Código TOTP inválido"}), 401
        
        log_security_event('admin_2fa_verify_success', user_id=current_user_id)
        
        # Gerar novo token com 2FA verificado
        new_access_token = create_access_token(
            identity=str(user.id),
            additional_claims={
                'username': user.username,
                'is_admin': user.is_admin,
                'totp_verified': True,
                'fingerprint': get_jwt().get('fingerprint')
            }
        )
        
        return jsonify({
            "message": "2FA verificado com sucesso",
            "access_token": new_access_token,
            "totp_verified": True
        })
        
    except Exception as e:
        log_security_event('admin_2fa_verify_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao verificar 2FA"}), 500

@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@limiter.limit("10 per minute")
def admin_dashboard():
    """
    Dashboard admin com métricas do sistema.
    """
    try:
        print(f"🔐 DASHBOARD REQUEST - Starting dashboard")
        
        # Verificação admin simplificada
        current_user_id = get_jwt_identity()
        print(f"🔐 DASHBOARD REQUEST - User ID: {current_user_id}")
        
        user = User.query.get(current_user_id)
        if not user or not user.is_admin:
            print(f"🔐 DASHBOARD REQUEST - Admin access denied")
            return jsonify({"error": "Não autorizado"}), 401
            
        print(f"🔐 DASHBOARD REQUEST - Admin access verified: {user.username}")
        
        # Retornar dados simples primeiro
        return jsonify({
            "message": "Dashboard funcionando!",
            "user": user.username,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        print(f"🔐 DASHBOARD ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erro no dashboard: {str(e)}"}), 500
        
        # Atividade suspeita (últimas 24h)
        from utils.audit import AuditLogger
        security_summary = AuditLogger.get_security_summary(hours=24)
        
        dashboard_data = {
            "overview": {
                "total_users": total_users,
                "total_posts": total_posts,
                "total_messages": total_messages,
                "pending_reports": pending_reports,
                "new_users_week": new_users,
                "new_posts_day": new_posts
            },
            "security": security_summary,
            "system_health": {
                "database_status": "healthy",  # Em produção, verificar conexão real
                "redis_status": "healthy",     # Em produção, verificar Redis
                "storage_status": "healthy"
            }
        }
        
        log_admin_action('dashboard_view', str(admin_user.id))
        
        return jsonify(dashboard_data)
        
    except Exception as e:
        log_security_event('admin_dashboard_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao carregar dashboard"}), 500

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@limiter.limit("20 per minute")
def admin_users():
    """
    Lista usuários com filtros e paginação.
    """
    try:
        admin_user = verify_admin_access()
        
        # Validação de parâmetros
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 50)
        
        # Filtros
        status_filter = request.args.get('status', 'all')  # all, active, banned, admin
        search = request.args.get('search', '').strip()
        
        # Query base
        users_query = User.query
        
        # Aplicar filtros
        if status_filter == 'active':
            users_query = users_query.filter_by(is_banned=False)
        elif status_filter == 'banned':
            users_query = users_query.filter_by(is_banned=True)
        elif status_filter == 'admin':
            users_query = users_query.filter_by(is_admin=True)
        
        # Busca
        if search:
            users_query = users_query.filter(
                or_(
                    User.username.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%')
                )
            )
        
        # Ordenação e paginação
        users = users_query.order_by(desc(User.created_at)).offset((page - 1) * limit).limit(limit).all()
        total = users_query.count()
        
        results = []
        for user in users:
            # Estatísticas do usuário
            posts_count = user.posts.count()
            followers_count = user.following.filter_by(status='accepted').count()
            
            # Perfil de comportamento
            behavior_profile = get_user_behavior_profile(str(user.id), days=7)
            
            results.append({
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_banned": user.is_banned,
                "is_private": user.is_private,
                "created_at": user.created_at.isoformat(),
                "last_login": user.updated_at.isoformat() if user.updated_at else None,
                "stats": {
                    "posts_count": posts_count,
                    "followers_count": followers_count
                },
                "behavior": {
                    "humanity_score": behavior_profile.get('humanity_score', 0),
                    "is_suspicious": behavior_profile.get('is_suspicious', False)
                }
            })
        
        log_admin_action('users_list', str(admin_user.id), details={
            'status_filter': status_filter,
            'search': search,
            'page': page
        })
        
        return jsonify({
            "users": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('admin_users_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao listar usuários"}), 500

@admin_bp.route('/users/<user_id>', methods=['PUT'])
@jwt_required()
@limiter.limit("10 per minute")
def admin_update_user(user_id: str):
    """
    Atualiza usuário (ban/unban, admin status).
    """
    try:
        admin_user = verify_admin_access()
        
        # Validar campos
        data, errors = validate_endpoint_fields('admin_update_user', request.get_json())
        if errors:
            return jsonify({"error": "Dados inválidos", "details": errors}), 400
        
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({"error": "Usuário não encontrado"}), 404
        
        # Não permitir modificar a si mesmo
        if str(target_user.id) == str(admin_user.id):
            return jsonify({"error": "Não pode modificar seu próprio usuário"}), 400
        
        updated_fields = []
        
        # Atualizar campos permitidos
        if 'is_banned' in data:
            old_banned = target_user.is_banned
            target_user.is_banned = data['is_banned']
            updated_fields.append('is_banned')
            
            if old_banned != target_user.is_banned:
                action = 'ban' if target_user.is_banned else 'unban'
                log_admin_action(f'user_{action}', str(admin_user.id), 'user', user_id)
        
        if 'is_admin' in data and admin_user.is_admin:  # Apenas admins podem modificar admin status
            target_user.is_admin = data['is_admin']
            updated_fields.append('is_admin')
            log_admin_action('admin_status_change', str(admin_user.id), 'user', user_id)
        
        if 'is_private' in data:
            target_user.is_private = data['is_private']
            updated_fields.append('is_private')
        
        if updated_fields:
            target_user.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                "message": "Usuário atualizado com sucesso",
                "user": {
                    "id": str(target_user.id),
                    "username": target_user.username,
                    "is_admin": target_user.is_admin,
                    "is_banned": target_user.is_banned,
                    "is_private": target_user.is_private,
                    "updated_fields": updated_fields
                }
            })
        else:
            return jsonify({"error": "Nenhum campo para atualizar"}), 400
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        log_security_event('admin_update_user_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_user_id': user_id})
        return jsonify({"error": "Erro ao atualizar usuário"}), 500

@admin_bp.route('/reports', methods=['GET'])
@jwt_required()
@limiter.limit("20 per minute")
def admin_reports():
    """
    Lista denúncias pendentes.
    """
    try:
        admin_user = verify_admin_access()
        
        # Validação de paginação
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 50)
        
        status_filter = request.args.get('status', 'pending')
        
        # Query base
        reports_query = Report.query
        
        if status_filter != 'all':
            reports_query = reports_query.filter_by(status=status_filter)
        
        # Ordenação e paginação
        reports = reports_query.order_by(desc(Report.created_at)).offset((page - 1) * limit).limit(limit).all()
        total = reports_query.count()
        
        results = []
        for report in reports:
            # Obter informações do alvo
            target_info = None
            if report.target_type == 'user':
                target_user = User.query.get(report.target_id)
                if target_user:
                    target_info = {
                        "id": str(target_user.id),
                        "username": target_user.username,
                        "is_banned": target_user.is_banned
                    }
            elif report.target_type == 'post':
                target_post = Post.query.get(report.target_id)
                if target_post:
                    target_info = {
                        "id": str(target_post.id),
                        "content": target_post.content[:100] + "..." if len(target_post.content) > 100 else target_post.content,
                        "author": str(target_post.user_id)
                    }
            
            # Informações do denunciante
            reporter = User.query.get(report.reporter_id)
            
            results.append({
                "id": str(report.id),
                "target_type": report.target_type,
                "target_info": target_info,
                "reason": report.reason,
                "status": report.status,
                "created_at": report.created_at.isoformat(),
                "reporter": {
                    "id": str(reporter.id),
                    "username": reporter.username
                } if reporter else None
            })
        
        log_admin_action('reports_view', str(admin_user.id), details={
            'status_filter': status_filter,
            'page': page
        })
        
        return jsonify({
            "reports": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('admin_reports_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao listar denúncias"}), 500

@admin_bp.route('/reports/<report_id>', methods=['PUT'])
@jwt_required()
@limiter.limit("10 per minute")
def admin_review_report(report_id: str):
    """
    Revisa denúncia.
    """
    try:
        admin_user = verify_admin_access()
        
        # Validar campos
        data, errors = validate_endpoint_fields('admin_review_report', request.get_json())
        if errors:
            return jsonify({"error": "Dados inválidos", "details": errors}), 400
        
        status = data['status']
        if status not in ['pending', 'reviewed', 'dismissed']:
            return jsonify({"error": "Status inválido"}), 400
        
        report = Report.query.get(report_id)
        if not report:
            return jsonify({"error": "Denúncia não encontrada"}), 404
        
        old_status = report.status
        report.status = status
        db.session.commit()
        
        log_admin_action('report_review', str(admin_user.id), 'report', report_id,
                       details={'old_status': old_status, 'new_status': status})
        
        return jsonify({
            "message": "Denúncia revisada com sucesso",
            "report": {
                "id": str(report.id),
                "status": report.status
            }
        })
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        log_security_event('admin_review_report_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'report_id': report_id})
        return jsonify({"error": "Erro ao revisar denúncia"}), 500

@admin_bp.route('/security', methods=['GET'])
@jwt_required()
@limiter.limit("5 per minute")
def admin_security():
    """
    Painel de segurança com estatísticas e alertas.
    """
    try:
        admin_user = verify_admin_access()
        
        # Estatísticas de honeypot
        honeypot_stats = get_honeypot_statistics()
        
        # Estatísticas de auditoria
        from utils.audit import AuditLogger
        security_summary = AuditLogger.get_security_summary(hours=24)
        
        # Top IPs suspeitos
        suspicious_ips = []
        for ip, count in honeypot_stats.get('last_24h', {}).get('top_suspicious_ips', [])[:10]:
            suspicious_ips.append({
                "ip": ip,
                "access_count": count,
                "risk_level": "high" if count > 10 else "medium"
            })
        
        # Eventos críticos recentes
        critical_events = security_summary.get('critical_events', [])[:20]
        
        security_data = {
            "honeypot": honeypot_stats,
            "audit": security_summary,
            "suspicious_ips": suspicious_ips,
            "critical_events": critical_events,
            "system_alerts": {
                "high_risk_access": len([ip for ip in suspicious_ips if ip["risk_level"] == "high"]),
                "critical_events": len(critical_events),
                "honeypot_hits": honeypot_stats.get('last_24h', {}).get('total_accesses', 0)
            }
        }
        
        log_admin_action('security_view', str(admin_user.id))
        
        return jsonify(security_data)
        
    except Exception as e:
        log_security_event('admin_security_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao carregar painel de segurança"}), 500

@admin_bp.route('/logs', methods=['GET'])
@jwt_required()
@limiter.limit("5 per minute")
def admin_logs():
    """
    Visualização de logs de auditoria.
    """
    try:
        admin_user = verify_admin_access()
        
        # Validação de parâmetros
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 100)
        
        # Filtros
        event_filter = request.args.get('event', '')
        user_filter = request.args.get('user_id', '')
        hours_filter = int(request.args.get('hours', 24))
        
        # Query base
        logs_query = AuditLog.query
        
        # Filtro de tempo
        if hours_filter > 0:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_filter)
            logs_query = logs_query.filter(AuditLog.timestamp > cutoff_time)
        
        # Filtro de evento
        if event_filter:
            logs_query = logs_query.filter(AuditLog.action.ilike(f'%{event_filter}%'))
        
        # Filtro de usuário
        if user_filter:
            logs_query = logs_query.filter(AuditLog.user_id == user_filter)
        
        # Ordenação e paginação
        logs = logs_query.order_by(desc(AuditLog.timestamp)).offset((page - 1) * limit).limit(limit).all()
        total = logs_query.count()
        
        results = []
        for log in logs:
            results.append({
                "id": str(log.id),
                "action": log.action,
                "user_id": str(log.user_id) if log.user_id else None,
                "target_type": log.target_type,
                "target_id": str(log.target_id) if log.target_id else None,
                "ip": log.ip,
                "fingerprint": log.fingerprint,
                "resultado": log.resultado,
                "details": log.details_json,
                "timestamp": log.timestamp.isoformat()
            })
        
        log_admin_action('logs_view', str(admin_user.id), details={
            'event_filter': event_filter,
            'user_filter': user_filter,
            'hours_filter': hours_filter
        })
        
        return jsonify({
            "logs": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('admin_logs_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao carregar logs"}), 500

def register_admin_routes(app):
    """
    Registra rotas admin com caminho secreto.
    """
    try:
        admin_route = get_admin_route(app)
        
        # Registrar blueprint com prefixo secreto
        app.register_blueprint(admin_bp, url_prefix=admin_route)
        
        # Log de registro (sem revelar a rota)
        app.logger.info("Admin routes registered")
        
    except Exception as e:
        app.logger.error(f"Failed to register admin routes: {e}")
        raise
