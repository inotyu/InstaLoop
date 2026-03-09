from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_
from datetime import datetime

from models import User, Post, Follow, Block, Report
from extensions import db
from utils.security import verify_password, hash_password, validate_password_strength
from utils.validators import validate_endpoint_fields, ValidationError, validate_pagination_params
from utils.image_processor import process_upload, validate_image_file
from utils.audit import log_user_action, log_security_event
from utils.behavioral import detect_automated_behavior
from extensions import limiter

users_bp = Blueprint('users', __name__, url_prefix='/api/users')

def verify_ownership(user_id: str, resource_user_id: str = None):
    """
    Verifica se o usuário atual é dono do recurso ou tem permissão.
    Para IDOR protection: sempre retornar 404, nunca 403.
    """
    current_user_id = get_jwt_identity()
    
    # Se não for o próprio perfil, verificar se é admin
    if current_user_id != user_id:
        current_user = User.query.get(current_user_id)
        if not current_user or not current_user.is_admin:
            abort(404)  # IDOR protection: 404 em vez de 403
    
    return True

def check_user_visibility(target_user_id: str, current_user_id: str = None) -> bool:
    """
    Verifica se usuário pode ver perfil de outro usuário.
    """
    target_user = User.query.get(target_user_id)
    if not target_user or target_user.is_banned:
        return False
    
    # Usuário pode ver seu próprio perfil
    if current_user_id == target_user_id:
        return True
    
    # Admin pode ver qualquer perfil
    if current_user_id:
        current_user = User.query.get(current_user_id)
        if current_user and current_user.is_admin:
            return True
    
    # Se perfil for privado, verificar se há follow
    if target_user.is_private:
        if not current_user_id:
            return False
        
        # Verificar se está seguindo e foi aceito
        follow = Follow.query.filter_by(
            follower_id=current_user_id,
            following_id=target_user_id,
            status='accepted'
        ).first()
        
        return follow is not None
    
    # Perfil público
    return True

def check_block_relationship(user1_id: str, user2_id: str) -> bool:
    """
    Verifica se há bloqueio entre dois usuários.
    """
    block = Block.query.filter(
        or_(
            and_(Block.blocker_id == user1_id, Block.blocked_id == user2_id),
            and_(Block.blocker_id == user2_id, Block.blocked_id == user1_id)
        )
    ).first()
    
    return block is not None

@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
@limiter.limit("20 per minute")
def update_profile():
    """
    Atualiza perfil do usuário com validação de campos.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.is_banned:
            abort(404)
        
        # Validar campos
        data, errors = validate_endpoint_fields('user_update_profile', request.get_json())
        if errors:
            log_security_event('profile_update_failed', user_id=current_user_id,
                             details={'validation_errors': errors})
            return jsonify({"error": "Dados inválidos", "details": errors}), 400
        
        # Atualizar campos permitidos
        updated_fields = []
        
        if 'bio' in data:
            user.bio = data['bio']
            updated_fields.append('bio')
        
        if 'avatar_url' in data:
            user.avatar_url = data['avatar_url']
            updated_fields.append('avatar_url')
        
        if 'is_private' in data:
            user.is_private = data['is_private']
            updated_fields.append('is_private')
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        log_user_action('profile_update', current_user_id, 'user', current_user_id,
                       details={'updated_fields': updated_fields})
        
        return jsonify({
            "message": "Perfil atualizado com sucesso",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "bio": user.bio,
                "avatar_url": user.avatar_url,
                "is_private": user.is_private
            }
        })
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        log_security_event('profile_update_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao atualizar perfil"}), 500

@users_bp.route('/profile/<user_id>', methods=['GET'])
@jwt_required()
def get_profile(user_id: str):
    """
    Obtém perfil de usuário com proteção IDOR e privacidade.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar se usuário existe e não está banido
        user = User.query.get(user_id)
        if not user or user.is_banned:
            log_security_event('profile_view', user_id=current_user_id, 
                             details={'target_id': user_id, 'result': 'not_found'})
            abort(404)  # IDOR protection
        
        # Verificar bloqueio mútuo
        if check_block_relationship(current_user_id, user_id):
            log_security_event('profile_view_blocked', user_id=current_user_id,
                             details={'target_id': user_id, 'reason': 'blocked'})
            abort(404)
        
        # Verificar visibilidade do perfil
        # NOTA: Sempre mostrar perfil, mas limitar informações para privados
        is_following = False
        has_pending_request = False
        
        # Verificar relação de follow
        follow = Follow.query.filter_by(
            follower_id=current_user_id,
            following_id=user_id
        ).first()
        
        if follow:
            if follow.status == 'accepted':
                is_following = True
            elif follow.status == 'pending':
                has_pending_request = True
        
        # Verificar follow mútuo para mensagens
        can_message = False
        if follow and follow.status == 'accepted':
            reverse_follow = Follow.query.filter_by(
                follower_id=user_id,
                following_id=current_user_id,
                status='accepted'
            ).first()
            can_message = reverse_follow is not None
        
        # Coletar informações permitidas
        profile_data = {
            "id": str(user.id),
            "username": user.username,
            "avatar_url": user.avatar_url,
            "is_private": user.is_private,
            "created_at": user.created_at.isoformat()
        }
        
        # Limitar bio para perfis privados que não segue
        if user.is_private and current_user_id != user_id and not is_following and not has_pending_request:
            profile_data["bio"] = "Perfil privado"
        else:
            profile_data["bio"] = user.bio
        
        # Adicionar informações adicionais dependendo da visibilidade
        if current_user_id == user_id:
            # Próprio perfil: informações completas
            profile_data.update({
                "email": user.email,
                "is_admin": user.is_admin,
                "followers_count": user.followers.filter_by(status='accepted').count(),
                "following_count": user.following.filter_by(status='accepted').count(),
                "posts_count": user.posts.count(),
                "can_message": False
            })
        elif user.is_private and not is_following and not has_pending_request:
            # Perfil privado que não segue e não tem solicitação pendente: informações limitadas
            profile_data.update({
                "followers_count": None,  # Ocultar
                "following_count": None,  # Ocultar
                "posts_count": None,      # Ocultar
                "follow_status": "private",
                "is_following": False
            })
        else:
            # Perfil público, ou privado com solicitação pendente, ou privado que segue: informações públicas
            profile_data.update({
                "followers_count": user.followers.filter_by(status='accepted').count(),
                "following_count": user.following.filter_by(status='accepted').count(),
                "posts_count": user.posts.count()
            })
            
            # Determinar status do follow
            if has_pending_request:
                profile_data["follow_status"] = "pending"
                profile_data["is_following"] = False
                profile_data["can_message"] = False
            else:
                profile_data["follow_status"] = follow.status if follow else None
                profile_data["is_following"] = follow and follow.status == 'accepted'
                profile_data["can_message"] = can_message
        
        log_user_action('profile_view', current_user_id, 'user', user_id)
        
        return jsonify(profile_data)
        
    except Exception as e:
        if not isinstance(e, ValidationError):
            log_security_event('profile_view_error', user_id=get_jwt_identity(),
                             details={'error': str(e), 'target_id': user_id})
        raise

@users_bp.route('/upload-avatar', methods=['POST'])
@jwt_required()
@limiter.limit("5 per hour")
def upload_avatar():
    """
    Upload de avatar com validação de segurança.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.is_banned:
            abort(404)
        
        # Verificar se há arquivo
        if 'avatar' not in request.files:
            return jsonify({"error": "Nenhum arquivo fornecido"}), 400
        
        file = request.files['avatar']
        if file.filename == '':
            return jsonify({"error": "Nenhum arquivo selecionado"}), 400
        
        # Validar arquivo
        is_valid, errors = validate_image_file(file)
        if not is_valid:
            log_security_event('file_upload_blocked', user_id=current_user_id,
                             details={'validation_errors': errors})
            return jsonify({"error": "Arquivo inválido", "details": errors}), 400
        
        # Processar upload
        try:
            filename, metadata = process_upload(file)
            
            # Atualizar avatar do usuário
            user.avatar_url = f"/static/uploads/{filename}"
            user.updated_at = datetime.utcnow()
            db.session.commit()
            
            log_user_action('avatar_upload', current_user_id, 'user', current_user_id,
                           details={'filename': filename, 'metadata': metadata})
            
            return jsonify({
                "message": "Avatar atualizado com sucesso",
                "avatar_url": user.avatar_url
            })
            
        except Exception as upload_error:
            log_security_event('file_upload_failed', user_id=current_user_id,
                             details={'error': str(upload_error)})
            return jsonify({"error": "Erro ao processar imagem"}), 400
        
    except Exception as e:
        log_security_event('avatar_upload_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro interno do servidor"}), 500

@users_bp.route('/change-password', methods=['POST'])
@jwt_required()
@limiter.limit("3 per hour")
def change_password():
    """
    Alteração de senha com verificação da senha atual.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.is_banned:
            abort(404)
        
        # Validar campos
        data, errors = validate_endpoint_fields('user_change_password', request.get_json())
        if errors:
            return jsonify({"error": "Dados inválidos", "details": errors}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Verificar senha atual
        if not verify_password(current_password, user.password_hash):
            log_security_event('password_change_failed', user_id=current_user_id,
                             details={'reason': 'invalid_current_password'})
            return jsonify({"error": "Senha atual incorreta"}), 400
        
        # Validar força da nova senha
        is_strong, strength_errors = validate_password_strength(new_password)
        if not is_strong:
            return jsonify({"error": "Nova senha muito fraca", "details": strength_errors}), 400
        
        # Atualizar senha
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        log_user_action('password_change', current_user_id, 'user', current_user_id)
        
        return jsonify({"message": "Senha alterada com sucesso"})
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        log_security_event('password_change_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao alterar senha"}), 500

@users_bp.route('/follow/<user_id>', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def follow_user(user_id: str):
    """
    Seguir usuário com validações de privacidade.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Não pode seguir a si mesmo
        if current_user_id == user_id:
            return jsonify({"error": "Não pode seguir a si mesmo"}), 400
        
        # Verificar se usuário alvo existe
        target_user = User.query.get(user_id)
        if not target_user or target_user.is_banned:
            abort(404)
        
        # Verificar bloqueio
        if check_block_relationship(current_user_id, user_id):
            log_security_event('follow_blocked', user_id=current_user_id,
                             details={'target_id': user_id, 'reason': 'blocked'})
            abort(404)
        
        # Verificar se já segue
        existing_follow = Follow.query.filter_by(
            follower_id=current_user_id,
            following_id=user_id
        ).first()
        
        if existing_follow:
            if existing_follow.status == 'accepted':
                # Se já segue, cancelar follow (unfollow)
                db.session.delete(existing_follow)
                db.session.commit()
                
                log_user_action('user_unfollow', current_user_id, 'user', user_id)
                
                return jsonify({
                    "message": "Deixou de seguir com sucesso",
                    "status": "unfollowed",
                    "action": "unfollowed"
                })
            elif existing_follow.status == 'pending':
                # Se tem solicitação pendente, cancelar solicitação
                db.session.delete(existing_follow)
                db.session.commit()
                
                log_user_action('follow_request_cancelled', current_user_id, 'user', user_id)
                
                return jsonify({
                    "message": "Solicitação de follow cancelada",
                    "status": "cancelled",
                    "action": "cancelled"
                })
        
        # Criar solicitação de follow
        follow = Follow(
            follower_id=current_user_id,
            following_id=user_id,
            status='pending' if target_user.is_private else 'accepted'
        )
        
        db.session.add(follow)
        db.session.commit()
        
        log_user_action('user_follow', current_user_id, 'user', user_id,
                       details={'status': follow.status})
        
        return jsonify({
            "message": "Solicitação de follow enviada" if target_user.is_private else "Seguindo com sucesso",
            "status": follow.status,
            "action": "followed"
        })
        
    except Exception as e:
        db.session.rollback()
        log_security_event('follow_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': user_id})
        return jsonify({"error": "Erro ao seguir usuário"}), 500

@users_bp.route('/follow/<user_id>', methods=['DELETE'])
@jwt_required()
@limiter.limit("30 per minute")
def unfollow_user(user_id: str):
    """
    Deixar de seguir usuário.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Buscar relação de follow
        follow = Follow.query.filter_by(
            follower_id=current_user_id,
            following_id=user_id
        ).first()
        
        if not follow:
            return jsonify({"error": "Não segue este usuário"}), 400
        
        db.session.delete(follow)
        db.session.commit()
        
        log_user_action('user_unfollow', current_user_id, 'user', user_id)
        
        return jsonify({"message": "Deixou de seguir com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        log_security_event('unfollow_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': user_id})
        return jsonify({"error": "Erro ao deixar de seguir"}), 500

@users_bp.route('/block/<user_id>', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def block_user(user_id: str):
    """
    Bloquear usuário.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Não pode bloquear a si mesmo
        if current_user_id == user_id:
            return jsonify({"error": "Não pode bloquear a si mesmo"}), 400
        
        # Verificar se usuário alvo existe
        target_user = User.query.get(user_id)
        if not target_user or target_user.is_banned:
            abort(404)
        
        # Verificar se já bloqueou
        existing_block = Block.query.filter_by(
            blocker_id=current_user_id,
            blocked_id=user_id
        ).first()
        
        if existing_block:
            return jsonify({"error": "Usuário já bloqueado"}), 400
        
        # Remover follow existente (se houver)
        Follow.query.filter(
            or_(
                and_(Follow.follower_id == current_user_id, Follow.following_id == user_id),
                and_(Follow.follower_id == user_id, Follow.following_id == current_user_id)
            )
        ).delete()
        
        # Criar bloqueio
        block = Block(
            blocker_id=current_user_id,
            blocked_id=user_id
        )
        
        db.session.add(block)
        db.session.commit()
        
        log_user_action('user_blocked', current_user_id, 'user', user_id)
        
        return jsonify({"message": "Usuário bloqueado com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        log_security_event('block_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': user_id})
        return jsonify({"error": "Erro ao bloquear usuário"}), 500

@users_bp.route('/block/<user_id>', methods=['DELETE'])
@jwt_required()
@limiter.limit("30 per minute")
def unblock_user(user_id: str):
    """
    Desbloquear usuário.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Buscar bloqueio
        block = Block.query.filter_by(
            blocker_id=current_user_id,
            blocked_id=user_id
        ).first()
        
        if not block:
            return jsonify({"error": "Usuário não está bloqueado"}), 400
        
        db.session.delete(block)
        db.session.commit()
        
        log_user_action('user_unblocked', current_user_id, 'user', user_id)
        
        return jsonify({"message": "Usuário desbloqueado com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        log_security_event('unblock_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': user_id})
        return jsonify({"error": "Erro ao desbloquear usuário"}), 500

@users_bp.route('/search', methods=['GET'])
@jwt_required()
@limiter.limit("60 per minute")
def search_users():
    """
    Busca de usuários com paginação.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Validar parâmetros manualmente (sem usar validate_pagination_params)
        params = request.args.to_dict()
        errors = []
        
        # Validar page
        page = 1
        if 'page' in params:
            try:
                page = int(params['page'])
                if page < 1:
                    errors.append("Página deve ser maior que 0")
                elif page > 1000:
                    errors.append("Página não pode ser maior que 1000")
            except (ValueError, TypeError):
                errors.append("Página deve ser um número inteiro")
        
        # Validar limit
        limit = 20
        if 'limit' in params:
            try:
                limit = int(params['limit'])
                if limit < 1:
                    errors.append("Limit deve ser maior que 0")
                elif limit > 100:
                    errors.append("Limit não pode ser maior que 100")
            except (ValueError, TypeError):
                errors.append("Limit deve ser um número inteiro")
        
        if errors:
            return jsonify({"error": "Parâmetros inválidos", "details": errors}), 400
        
        query = params.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify({"error": "Query muito curta (mínimo 2 caracteres)"}), 400
        
        # Buscar usuários
        users_query = User.query.filter(
            and_(
                User.is_banned == False,
                or_(
                    User.username.ilike(f'%{query}%'),
                    User.bio.ilike(f'%{query}%')
                )
            )
        )
        
        # Se não for admin, mostrar todos os usuários (incluindo privados)
        # mas limitar informações de perfis privados que não segue
        current_user = User.query.get(current_user_id)
        if not current_user or not current_user.is_admin:
            # Subquery para usuários que segue
            followed_users = db.session.query(Follow.following_id).filter_by(
                follower_id=current_user_id,
                status='accepted'
            ).subquery()
            
            # NOTA: Não filtramos mais usuários privados da busca
            # A restrição será aplicada apenas nos dados retornados
        
        # Paginação
        users = users_query.offset((page - 1) * limit).limit(limit).all()
        total = users_query.count()
        
        # Filtrar resultados (remover bloqueados)
        results = []
        for user in users:
            if not check_block_relationship(current_user_id, str(user.id)):
                user_data = {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url,
                    "is_private": user.is_private
                }
                
                # Para perfis privados que não segue, limitar informações
                if user.is_private and current_user_id != str(user.id):
                    # Verificar se já segue ou tem solicitação pendente
                    follow = Follow.query.filter_by(
                        follower_id=current_user_id,
                        following_id=str(user.id)
                    ).first()
                    
                    if follow and follow.status == 'accepted':
                        # Se já segue, mostrar bio completa
                        user_data["bio"] = user.bio
                    else:
                        # Se não segue, mostrar bio limitada ou vazia
                        user_data["bio"] = "Perfil privado"
                        user_data["follow_status"] = follow.status if follow else None
                        user_data["is_following"] = follow and follow.status == 'accepted'
                else:
                    # Perfil público ou próprio perfil: mostrar bio completa
                    user_data["bio"] = user.bio
                    
                    # Adicionar status de follow para outros perfis
                    if current_user_id != str(user.id):
                        follow = Follow.query.filter_by(
                            follower_id=current_user_id,
                            following_id=str(user.id)
                        ).first()
                        user_data["follow_status"] = follow.status if follow else None
                        user_data["is_following"] = follow and follow.status == 'accepted'
                
                results.append(user_data)
        
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
        log_security_event('search_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'query': request.args.get('q')})
        return jsonify({"error": "Erro na busca"}), 500

@users_bp.route('/<user_id>/followers', methods=['GET'])
@jwt_required()
def get_followers(user_id: str):
    """
    Lista de seguidores com proteção de privacidade.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar permissão
        # Permitir ver seguidores de: próprio perfil, perfis públicos, e perfis privados que segue
        target_user = User.query.get(user_id)
        if not target_user or target_user.is_banned:
            abort(404)
        
        # Se for próprio perfil, sempre permitir
        if current_user_id == user_id:
            pass  # Permitir acesso
        # Se for perfil público, permitir
        elif not target_user.is_private:
            pass  # Permitir acesso
        # Se for perfil privado, verificar se segue
        else:
            follow = Follow.query.filter_by(
                follower_id=current_user_id,
                following_id=user_id,
                status='accepted'
            ).first()
            if not follow:
                abort(404)
        
        # Validação de paginação
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 20)
        
        # Buscar seguidores
        followers_query = Follow.query.filter_by(
            following_id=user_id,
            status='accepted'
        ).join(User, Follow.follower_id == User.id)
        
        followers = followers_query.offset((page - 1) * limit).limit(limit).all()
        total = followers_query.count()
        
        results = []
        for follow in followers:
            follower = follow.follower
            if not check_block_relationship(current_user_id, str(follower.id)):
                results.append({
                    "id": str(follower.id),
                    "username": follower.username,
                    "avatar_url": follower.avatar_url,
                    "is_private": follower.is_private
                })
        
        return jsonify({
            "followers": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('followers_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': user_id})
        return jsonify({"error": "Erro ao buscar seguidores"}), 500

@users_bp.route('/follow-requests', methods=['GET'])
@jwt_required()
@limiter.limit("60 per minute")
def get_follow_requests():
    """
    Lista solicitações de follow pendentes recebidas pelo usuário atual.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Buscar solicitações pendentes onde o usuário atual é o alvo
        pending_requests = Follow.query.filter_by(
            following_id=current_user_id,
            status='pending'
        ).join(User, Follow.follower_id == User.id).all()
        
        # Formatar resposta
        requests_data = []
        for follow in pending_requests:
            follower = follow.follower
            if not check_block_relationship(current_user_id, str(follower.id)):
                requests_data.append({
                    "id": str(follow.id),
                    "follower": {
                        "id": str(follower.id),
                        "username": follower.username,
                        "avatar_url": follower.avatar_url
                    },
                    "created_at": follow.created_at.isoformat()
                })
        
        log_user_action('follow_requests_view', current_user_id, 'user', current_user_id)
        
        return jsonify({
            "requests": requests_data,
            "total": len(requests_data)
        })
        
    except Exception as e:
        log_security_event('follow_requests_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao buscar solicitações"}), 500

@users_bp.route('/follow-request/<request_id>/accept', methods=['POST'])
@jwt_required()
@limiter.limit("60 per minute")
def accept_follow_request(request_id: str):
    """
    Aceita uma solicitação de follow pendente.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Buscar a solicitação
        follow_request = Follow.query.get(request_id)
        if not follow_request:
            abort(404)
        
        # Verificar se o usuário atual é o alvo da solicitação
        if str(follow_request.following_id) != current_user_id:
            abort(404)
        
        # Verificar se ainda está pendente
        if follow_request.status != 'pending':
            return jsonify({"error": "Solicitação já foi processada"}), 400
        
        # Aceitar a solicitação
        follow_request.status = 'accepted'
        follow_request.updated_at = datetime.utcnow()
        db.session.commit()
        
        log_user_action('follow_request_accepted', current_user_id, 'user', str(follow_request.follower_id),
                       details={'request_id': request_id})
        
        return jsonify({
            "message": "Solicitação aceita com sucesso",
            "status": "accepted"
        })
        
    except Exception as e:
        db.session.rollback()
        log_security_event('follow_request_accept_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'request_id': request_id})
        return jsonify({"error": "Erro ao aceitar solicitação"}), 500

@users_bp.route('/follow-request/<request_id>/reject', methods=['POST'])
@jwt_required()
@limiter.limit("60 per minute")
def reject_follow_request(request_id: str):
    """
    Rejeita uma solicitação de follow pendente.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Buscar a solicitação
        follow_request = Follow.query.get(request_id)
        if not follow_request:
            abort(404)
        
        # Verificar se o usuário atual é o alvo da solicitação
        if str(follow_request.following_id) != current_user_id:
            abort(404)
        
        # Verificar se ainda está pendente
        if follow_request.status != 'pending':
            return jsonify({"error": "Solicitação já foi processada"}), 400
        
        # Rejeitar a solicitação (remover)
        db.session.delete(follow_request)
        db.session.commit()
        
        log_user_action('follow_request_rejected', current_user_id, 'user', str(follow_request.follower_id),
                       details={'request_id': request_id})
        
        return jsonify({
            "message": "Solicitação rejeitada",
            "status": "rejected"
        })
        
    except Exception as e:
        db.session.rollback()
        log_security_event('follow_request_reject_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'request_id': request_id})
        return jsonify({"error": "Erro ao rejeitar solicitação"}), 500

@users_bp.route('/<user_id>/following', methods=['GET'])
@jwt_required()
def get_following(user_id: str):
    """
    Lista de usuários seguidos com proteção de privacidade.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar permissão
        # Permitir ver seguindo de: próprio perfil, perfis públicos, e perfis privados que segue
        target_user = User.query.get(user_id)
        if not target_user or target_user.is_banned:
            abort(404)
        
        # Se for próprio perfil, sempre permitir
        if current_user_id == user_id:
            pass  # Permitir acesso
        # Se for perfil público, permitir
        elif not target_user.is_private:
            pass  # Permitir acesso
        # Se for perfil privado, verificar se segue
        else:
            follow = Follow.query.filter_by(
                follower_id=current_user_id,
                following_id=user_id,
                status='accepted'
            ).first()
            if not follow:
                abort(404)
        
        # Validação de paginação
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 20)
        
        # Buscar usuários seguidos
        following_query = Follow.query.filter_by(
            follower_id=user_id,
            status='accepted'
        ).join(User, Follow.following_id == User.id)
        
        following = following_query.offset((page - 1) * limit).limit(limit).all()
        total = following_query.count()
        
        results = []
        for follow in following:
            followed_user = follow.following
            if not check_block_relationship(current_user_id, str(followed_user.id)):
                results.append({
                    "id": str(followed_user.id),
                    "username": followed_user.username,
                    "avatar_url": followed_user.avatar_url,
                    "is_private": followed_user.is_private
                })
        
        return jsonify({
            "following": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('following_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': user_id})
        return jsonify({"error": "Erro ao buscar seguidos"}), 500
