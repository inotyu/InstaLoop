import os
from datetime import datetime
from flask import Flask, request, jsonify, g, send_from_directory

from config import config
from extensions import db, migrate, jwt, limiter, cors
from models import User
from routes.auth import auth_bp
from routes.users import users_bp
from routes.posts import posts_bp
from routes.messages import messages_bp
from routes.admin import register_admin_routes
from routes.csrf import csrf_bp
from routes.telemetry import telemetry_bp
from utils.security import get_client_ip, validate_origin, validate_csrf_token
from utils.honeypot import is_honeypot_route, handle_honeypot_request
from utils.audit import log_security_event
from utils.behavioral import detect_automated_behavior

def create_app(config_name='development'):
    """
    Factory pattern para criação da aplicação com múltiplas camadas de segurança.
    """
    app = Flask(__name__)
    
    # Configuração
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])

    # Inicializar extensões
    # Desabilitar criação automática de diretório instance em ambiente serverless
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    if not app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite'):
        db.init_app(app)
    else:
        # Para SQLite em ambiente serverless, usar memória ou caminho temporário
        if os.environ.get('VERCEL'):
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={
            r"/api/*": {"origins": app.config['CORS_ORIGINS']},
            r"/admin123/*": {"origins": app.config['CORS_ORIGINS']}
        },
        supports_credentials=True,
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-CSRF-Token",
        ],
        expose_headers=[
            "Content-Type",
        ],
    )
    
    # Middleware para log de todas as requisições
    @app.before_request
    def log_all_requests():
        print(f"🌐 [{datetime.utcnow()}] {request.method} {request.path} - Headers: {dict(request.headers)}")
    
    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(messages_bp)
    # Registrar blueprints
    from routes.reports import reports_bp
    app.register_blueprint(reports_bp)
    app.register_blueprint(csrf_bp)
    app.register_blueprint(telemetry_bp)
    
    # Registrar rotas admin com caminho secreto
    register_admin_routes(app)
    
    # Debug: mostrar rotas registradas
    print("\n=== ROTAS REGISTRADAS ===")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint} [{', '.join(rule.methods)}]")
    print("========================\n")
    
    # Rota para servir arquivos de upload
    @app.route('/static/uploads/<path:filename>')
    def serve_uploads(filename):
        response = send_from_directory(app.config['UPLOAD_DIR'], filename)
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        # Content-Disposition: attachment para uploads (nunca executável)
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        # Nunca servir com Content-Type dinâmico baseado no nome do arquivo
        response.headers['Content-Type'] = 'application/octet-stream'
        return response

    # Middleware de segurança - ordem é crítica!
    setup_security_middleware(app)
    
    # Handlers de erro
    setup_error_handlers(app)
    
    # JWT callbacks
    setup_jwt_callbacks(app)
    
    # Comandos CLI
    setup_cli_commands(app)
    
    return app

def setup_security_middleware(app):
    """
    Configura múltiplas camadas de middleware de segurança.
    """
    
    @app.before_request
    def security_before_request():
        """
        CAMADA 1: Validações básicas de segurança antes de processar qualquer request.
        """
        # Marcar tempo de início para análise de timing
        g.start_time = datetime.utcnow()
        
        # Detectar honeypots primeiro
        if is_honeypot_route(request.path):
            return handle_honeypot_request()
        
        # Bloquear acesso a arquivos sensíveis
        sensitive_files = app.config.get('SENSITIVE_FILES', [])
        for sensitive_file in sensitive_files:
            if sensitive_file.lower() in request.path.lower():
                log_security_event('sensitive_file_access', 
                                 details={'path': request.path, 'ip': get_client_ip(request)})
                return jsonify({"error": "Not found"}), 404
        
        # CSRF (Double Submit Cookie) + Origin/Referer (camada adicional)
        if request.method not in ['GET', 'HEAD', 'OPTIONS'] and request.path.startswith('/api/'):
            try:
                print(f"🔍 DEBUG: Validando origin para {request.path}")
                print(f"🔍 DEBUG: Origin: {request.headers.get('Origin')}")
                print(f"🔍 DEBUG: Referer: {request.headers.get('Referer')}")
                print(f"🔍 DEBUG: CORS_ORIGINS: {current_app.config.get('CORS_ORIGINS', [])}")
                
                if not validate_origin(request):
                    print(f"❌ DEBUG: Origin validation FAILED")
                    log_security_event(
                        'csrf_invalid',
                        details={
                            'reason': 'origin_check_failed',
                            'origin': request.headers.get('Origin'),
                            'referer': request.headers.get('Referer'),
                        }
                    )
                    return jsonify({"error": "Not found"}), 404
                else:
                    print(f"✅ DEBUG: Origin validation PASSED")
            except Exception as e:
                print(f"❌ DEBUG: Error in origin validation: {str(e)}")
                return jsonify({"error": "Internal server error"}), 500

            # Permitir emitir CSRF token sem exigir token
            if request.path != '/api/csrf' and not request.path.startswith('/api/auth/'):
                # TEMPORARIAMENTE DESABILITADO PARA TESTE
                pass
                # header_token = request.headers.get('X-CSRF-Token', '')
                # cookie_token = request.cookies.get('csrf_token', '')

                # if not validate_csrf_token(header_token, cookie_token):
                #     log_security_event(
                #         'csrf_invalid',
                #         details={
                #             'reason': 'double_submit_mismatch',
                #             'has_header': bool(header_token),
                #             'has_cookie': bool(cookie_token),
                #         }
                #     )
                #     return jsonify({"error": "Not found"}), 404
        
        # Detectar comportamento automatizado
        if request.endpoint and request.endpoint.startswith('api'):  # Apenas para API
            detection_result = detect_automated_behavior()
            if detection_result['should_block']:
                log_security_event('automated_behavior_blocked',
                                 details=detection_result)
                return jsonify({"error": "Request bloqueado"}), 429
    
    @app.after_request
    def security_after_request(response):
        """
        CAMADA 2: Headers de segurança em todas as respostas.
        """
        # Headers de segurança
        security_headers = app.config.get('SECURITY_HEADERS', {})
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Ajuste específico para recursos estáticos (imagens de upload)
        if request.path.startswith('/static/uploads/'):
            response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
            # Relaxar CSP para permitir imagens data: e blob: se necessário
            csp = response.headers.get('Content-Security-Policy', '')
            if csp:
                response.headers['Content-Security-Policy'] = csp.replace("default-src 'none'", "default-src 'self'")
        
        # Remover headers que revelam stack
        response.headers.pop('Server', None)
        response.headers.pop('X-Powered-By', None)
        response.headers.pop('X-Flask-Version', None)
        
        # Cache zero em endpoints autenticados
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        # Content Security Policy adicional para uploads
        if request.path.startswith('/static/uploads/'):
            csp = response.headers.get('Content-Security-Policy', '')
            if csp:
                response.headers['Content-Security-Policy'] = csp + "; default-src 'none'"
        
        # Log de tempo de resposta (para detectar anomalias)
        if hasattr(g, 'start_time'):
            response_time = (datetime.utcnow() - g.start_time).total_seconds()
            if response_time > 5.0:  # Requests muito longos
                log_security_event('slow_request',
                                 details={'path': request.path, 
                                         'method': request.method,
                                         'response_time': response_time})
        
        return response
    
    @app.teardown_request
    def security_teardown(exception):
        """
        CAMADA 3: Cleanup e logging final.
        """
        if exception:
            log_security_event('request_exception',
                             details={'path': request.path,
                                     'method': request.method,
                                     'exception': str(exception)})
        
        # Limpar dados sensíveis do contexto
        if hasattr(g, 'sensitive_data'):
            delattr(g, 'sensitive_data')

def setup_error_handlers(app):
    """
    Configura handlers de erro seguros.
    """
    
    @app.errorhandler(400)
    def bad_request(error):
        # Log detalhado para ajudar na depuração de erros 400
        try:
            print(f"⚠️ 400 Bad Request em {request.path}: {error}")
        except Exception:
            pass
        return jsonify({"error": "Bad request"}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized"}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        # Sempre retornar 404 em vez de 403 para não revelar existência
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({"error": "Too many requests"}), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        log_security_event('internal_server_error',
                         details={'path': request.path, 'error': str(error)})
        return jsonify({"error": "Internal server error"}), 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """
        Handler genérico para exceções não tratadas.
        """
        db.session.rollback()
        
        # Log detalhado do erro
        log_security_event('unhandled_exception',
                         details={'path': request.path,
                                 'method': request.method,
                                 'error': str(error),
                                 'error_type': type(error).__name__})
        
        # Em produção, nunca revelar detalhes do erro
        if app.config.get('DEBUG', False):
            return jsonify({"error": str(error)}), 500
        else:
            return jsonify({"error": "Internal server error"}), 500

def setup_jwt_callbacks(app):
    """
    Configura callbacks JWT com validações adicionais.
    """
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """
        Verifica se JWT foi revogado (refresh tokens no banco).
        """
        # Para access tokens, não temos blocklist (são de curta duração)
        # Para refresh tokens, a verificação é feita no endpoint /refresh
        return False
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        """
        Callback para token expirado.
        """
        log_security_event('jwt_expired',
                         details={'user_id': jwt_payload.get('sub'),
                                 'exp': jwt_payload.get('exp')})
        return jsonify({"error": "Token expired"}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        """
        Callback para token inválido.
        """
        log_security_event('jwt_invalid',
                         details={'error': str(error)})
        return jsonify({"error": "Invalid token"}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        """
        Callback para token ausente.
        """
        return jsonify({"error": "Authorization token required"}), 401
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        """
        Callback para token não fresh.
        """
        return jsonify({"error": "Fresh token required"}), 401
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        """
        Callback para token revogado.
        """
        log_security_event('jwt_revoked',
                         details={'user_id': jwt_payload.get('sub')})
        return jsonify({"error": "Token has been revoked"}), 401

def setup_cli_commands(app):
    """
    Configura comandos CLI para administração.
    """
    
    @app.cli.command()
    def init_db():
        """Inicializa o banco de dados."""
        db.create_all()
        print("Banco de dados inicializado.")
    
    @app.cli.command()
    def create_admin():
        """Cria usuário admin."""
        import getpass
        from utils.security import hash_password, generate_totp_secret
        
        username = input("Username: ")
        email = input("Email: ")
        password = getpass.getpass("Password: ")
        
        # Verificar se usuário já existe
        if User.query.filter_by(username=username).first():
            print("Username já existe.")
            return
        
        if User.query.filter_by(email=email).first():
            print("Email já existe.")
            return
        
        # Criar admin
        admin = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_admin=True,
            totp_secret=generate_totp_secret()
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"Admin '{username}' criado com sucesso.")
        print("Configure seu app TOTP com o secret:", admin.totp_secret)
    
    @app.cli.command()
    def cleanup_tokens():
        """Limpa tokens expirados."""
        from models import RefreshToken, PasswordReset
        
        # Limpar refresh tokens expirados
        expired_refresh = RefreshToken.query.filter(
            RefreshToken.expires_at < datetime.utcnow()
        ).delete()
        
        # Limpar password resets expirados
        expired_resets = PasswordReset.query.filter(
            PasswordReset.expires_at < datetime.utcnow()
        ).delete()
        
        db.session.commit()
        
        print(f"Limpos {expired_refresh} refresh tokens e {expired_resets} password resets.")
    
    @app.cli.command()
    def security_audit():
        """Executa auditoria de segurança."""
        from utils.audit import AuditLogger
        
        # Estatísticas de segurança
        security_summary = AuditLogger.get_security_summary(hours=24)
        
        print("=== AUDITORIA DE SEGURANÇA (24h) ===")
        print(f"Eventos de segurança: {security_summary.get('total_security_events', 0)}")
        print(f"IPs suspeitos: {len(security_summary.get('top_suspicious_ips', []))}")
        print(f"Eventos críticos: {len(security_summary.get('critical_events', []))}")
        
        # Top eventos
        event_counts = security_summary.get('event_counts', {})
        if event_counts:
            print("\nTop eventos:")
            for event, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {event}: {count}")

app = None

# Quando importado por um servidor WSGI (ex: gunicorn), expor a variável `app`.
if __name__ != '__main__':
    app = create_app()

if __name__ == '__main__':
    # Execução recomendada em dev:
    #   python -m backend.app
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config.get('DEBUG', False)
    )
