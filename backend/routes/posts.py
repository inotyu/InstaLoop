from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_, desc, func
from datetime import datetime

from models import Post, Comment, Like, User, Follow, Block, Report
from extensions import db
from utils.security import sanitize_input
from utils.validators import validate_endpoint_fields, ValidationError, validate_pagination_params
from utils.image_processor import process_upload, validate_image_file
from utils.audit import log_user_action, log_security_event
from utils.behavioral import detect_automated_behavior
from extensions import limiter

posts_bp = Blueprint('posts', __name__, url_prefix='/api/posts')

def verify_post_ownership(post_id: str, user_id: str = None):
    """
    Verifica se usuário é dono do post com proteção IDOR.
    """
    if user_id is None:
        user_id = get_jwt_identity()
    
    post = Post.query.get(post_id)
    if not post or str(post.user_id) != user_id:
        abort(404)  # IDOR protection: sempre 404
    
    return post

def verify_comment_ownership(comment_id: str, user_id: str = None):
    """
    Verifica se usuário é dono do comentário com proteção IDOR.
    """
    if user_id is None:
        user_id = get_jwt_identity()
    
    comment = Comment.query.get(comment_id)
    if not comment or str(comment.user_id) != user_id:
        abort(404)  # IDOR protection: sempre 404
    
    return comment

def check_post_visibility(post: Post, current_user_id: str = None) -> bool:
    """
    Verifica se usuário pode ver o post.
    """
    # Post não existe ou autor está banido
    if not post or post.author.is_banned:
        return False
    
    # Post do próprio usuário
    if current_user_id and str(post.user_id) == current_user_id:
        return True
    
    # Verificar se autor está bloqueado
    if current_user_id and check_block_relationship(current_user_id, str(post.user_id)):
        return False
    
    # Se perfil do autor for privado, verificar se segue
    if post.author.is_private:
        if not current_user_id:
            return False
        
        follow = Follow.query.filter_by(
            follower_id=current_user_id,
            following_id=str(post.user_id),
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

@posts_bp.route('', methods=['POST'])
@jwt_required()
@limiter.limit("20 per hour")
def create_post():
    """
    Cria novo post com validação e sanitização.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.is_banned:
            abort(404)
        
        # Validar campos
        data, errors = validate_endpoint_fields('post_create', request.get_json())
        if errors:
            log_security_event('post_create_failed', user_id=current_user_id,
                             details={'validation_errors': errors})
            return jsonify({"error": "Dados inválidos", "details": errors}), 400
        
        content = data.get('content', '').strip()
        media_url = data.get('media_url')
        
        # Validar que há conteúdo ou mídia
        if not content and not media_url:
            return jsonify({"error": "Post deve ter conteúdo ou mídia"}), 400
        
        # Sanitizar conteúdo
        if content:
            content = sanitize_input(content)
            if len(content) > 2000:
                return jsonify({"error": "Conteúdo muito longo (máximo 2000 caracteres)"}), 400
        
        # Criar post
        post = Post(
            user_id=current_user_id,
            content=content,
            media_url=media_url
        )
        
        db.session.add(post)
        db.session.commit()
        
        log_user_action('post_create', current_user_id, 'post', str(post.id),
                       details={'has_content': bool(content), 'has_media': bool(media_url)})
        
        return jsonify({
            "message": "Post criado com sucesso",
            "post": {
                "id": str(post.id),
                "content": post.content,
                "media_url": post.media_url,
                "created_at": post.created_at.isoformat(),
                "author": {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url
                }
            }
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        log_security_event('post_create_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao criar post"}), 500

@posts_bp.route('/create', methods=['POST'])
@jwt_required()
@limiter.limit("20 per hour")
def create_post_with_media():
    """
    Cria novo post com texto e/ou mídia.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.is_banned:
            abort(404)
        
        # Verificar se é multipart/form-data
        if not request.is_json and request.files:
            # Upload com mídia
            if 'media' not in request.files:
                return jsonify({"error": "Nenhum arquivo fornecido"}), 400
            
            file = request.files['media']
            if file.filename == '':
                return jsonify({"error": "Nenhum arquivo selecionado"}), 400
            
            # Validar arquivo
            is_valid, errors = validate_image_file(file)
            if not is_valid:
                log_security_event('file_upload_blocked', user_id=current_user_id,
                                 details={'validation_errors': errors})
                return jsonify({"error": "Arquivo inválido", "details": errors}), 400
            
            # Processar upload
            filename, metadata = process_upload(file)
            media_url = f"/static/uploads/{filename}"
            
            # Obter conteúdo do texto
            content = request.form.get('content', '').strip()
        else:
            # Post apenas com texto
            data = request.get_json()
            if not data:
                return jsonify({"error": "Dados inválidos"}), 400
            
            content = data.get('content', '').strip()
            media_url = None
        
        # Validar que há conteúdo ou mídia
        if not content and not media_url:
            return jsonify({"error": "Post deve ter conteúdo ou mídia"}), 400
        
        # Sanitizar conteúdo
        if content:
            content = sanitize_input(content)
            if len(content) > 2000:
                return jsonify({"error": "Conteúdo muito longo (máximo 2000 caracteres)"}), 400
        
        # Criar post
        post = Post(
            user_id=current_user_id,
            content=content,
            media_url=media_url
        )
        
        db.session.add(post)
        db.session.commit()
        
        log_user_action('post_create', current_user_id, 'post', str(post.id),
                       details={'has_content': bool(content), 'has_media': bool(media_url)})
        
        return jsonify({
            "message": "Post criado com sucesso",
            "post": {
                "id": str(post.id),
                "user_id": str(post.user_id),
                "content": post.content,
                "media_url": post.media_url,
                "created_at": post.created_at.isoformat(),
                "likes_count": 0,
                "comments_count": 0,
                "is_liked": False,
                "comments": [],
                "author": {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url
                }
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        log_security_event('post_create_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao criar post"}), 500

@posts_bp.route('/upload-media', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def upload_media():
    """
    Upload de mídia para posts.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.is_banned:
            abort(404)
        
        # Verificar se há arquivo
        if 'media' not in request.files:
            return jsonify({"error": "Nenhum arquivo fornecido"}), 400
        
        file = request.files['media']
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
            media_url = f"/static/uploads/{filename}"
            
            log_user_action('media_upload', current_user_id, 'post', current_user_id,
                           details={'filename': filename, 'metadata': metadata})
            
            return jsonify({
                "message": "Mídia enviada com sucesso",
                "media_url": media_url
            })
            
        except Exception as upload_error:
            log_security_event('file_upload_failed', user_id=current_user_id,
                             details={'error': str(upload_error)})
            return jsonify({"error": "Erro ao processar mídia"}), 400
        
    except Exception as e:
        log_security_event('media_upload_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro interno do servidor"}), 500

@posts_bp.route('/<post_id>', methods=['GET'])
@jwt_required()
def get_post(post_id: str):
    """
    Obtém post específico com verificações de visibilidade.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Buscar post (já faz verificação de existência)
        post = Post.query.get(post_id)
        if not post:
            log_security_event('post_view_failed', user_id=current_user_id,
                             details={'target_id': post_id, 'result': 'not_found'})
            abort(404)
        
        # Verificar visibilidade
        if not check_post_visibility(post, current_user_id):
            log_security_event('post_view_blocked', user_id=current_user_id,
                             details={'target_id': post_id, 'result': 'not_visible'})
            abort(404)
        
        # Contar likes e comentários
        likes_count = Like.query.filter_by(post_id=post_id).count()
        comments_count = Comment.query.filter_by(post_id=post_id).count()
        
        # Carregar comentários recentes (últimos 10)
        recent_comments = Comment.query.filter_by(post_id=post_id).order_by(desc(Comment.created_at)).limit(10).all()
        comments_data = []
        for comment in recent_comments:
            # Verificar se autor do comentário está bloqueado
            if not check_block_relationship(current_user_id, str(comment.user_id)):
                comments_data.append({
                    "id": str(comment.id),
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat(),
                    "author": {
                        "id": str(comment.author.id),
                        "username": comment.author.username,
                        "avatar_url": comment.author.avatar_url
                    }
                })
        
        # Verificar se usuário curtiu
        is_liked = False
        if current_user_id:
            like = Like.query.filter_by(
                post_id=post_id,
                user_id=current_user_id
            ).first()
            is_liked = like is not None
        
        post_data = {
            "id": str(post.id),
            "user_id": str(post.user_id),
            "content": post.content,
            "media_url": post.media_url,
            "created_at": post.created_at.isoformat(),
            "updated_at": post.updated_at.isoformat(),
            "likes_count": likes_count,
            "comments_count": comments_count,
            "is_liked": is_liked,
            "comments": comments_data,
            "author": {
                "id": str(post.author.id),
                "username": post.author.username,
                "avatar_url": post.author.avatar_url,
                "is_private": post.author.is_private
            }
        }
        
        log_user_action('post_view', current_user_id, 'post', post_id)
        
        return jsonify(post_data)
        
    except Exception as e:
        if not isinstance(e, ValidationError):
            log_security_event('post_view_error', user_id=get_jwt_identity(),
                             details={'error': str(e), 'target_id': post_id})
        raise

@posts_bp.route('/<post_id>', methods=['PUT'])
@jwt_required()
@limiter.limit("30 per hour")
def update_post(post_id: str):
    """
    Atualiza post com verificação de ownership.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar ownership
        post = verify_post_ownership(post_id, current_user_id)
        
        # Validar campos
        data, errors = validate_endpoint_fields('post_update', request.get_json())
        if errors:
            log_security_event('post_update_failed', user_id=current_user_id,
                             details={'validation_errors': errors})
            return jsonify({"error": "Dados inválidos", "details": errors}), 400
        
        content = data.get('content', '').strip()
        media_url = data.get('media_url')
        
        # Determinar valores finais (usar atual se não fornecido)
        final_content = content if 'content' in data else (post.content or '')
        final_media_url = media_url if 'media_url' in data else post.media_url
        
        # Validar que o post resultante terá conteúdo ou mídia
        if not final_content.strip() and not final_media_url:
            return jsonify({"error": "Post deve ter conteúdo ou mídia"}), 400
        
        # Sanitizar conteúdo apenas se foi fornecido
        if 'content' in data:
            if content:
                final_content = sanitize_input(content)
                if len(final_content) > 2000:
                    return jsonify({"error": "Conteúdo muito longo (máximo 2000 caracteres)"}), 400
            else:
                final_content = content  # vazio
        
        # Atualizar apenas os campos fornecidos
        if 'content' in data:
            post.content = final_content
        if 'media_url' in data:
            post.media_url = final_media_url
        post.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        log_user_action('post_update', current_user_id, 'post', post_id,
                       details={'has_content': bool(content), 'has_media': bool(media_url)})
        
        return jsonify({
            "message": "Post atualizado com sucesso",
            "post": {
                "id": str(post.id),
                "content": post.content,
                "media_url": post.media_url,
                "updated_at": post.updated_at.isoformat()
            }
        })
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        log_security_event('post_update_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': post_id})
        return jsonify({"error": "Erro ao atualizar post"}), 500

@posts_bp.route('/<post_id>', methods=['DELETE'])
@jwt_required()
@limiter.limit("20 per hour")
def delete_post(post_id: str):
    """
    Deleta post com verificação de ownership.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar ownership
        post = verify_post_ownership(post_id, current_user_id)
        
        # Deletar post (cascade deletará comentários e likes)
        db.session.delete(post)
        db.session.commit()
        
        log_user_action('post_delete', current_user_id, 'post', post_id)
        
        return jsonify({"message": "Post deletado com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        log_security_event('post_delete_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': post_id})
        return jsonify({"error": "Erro ao deletar post"}), 500

@posts_bp.route('/comment/<comment_id>', methods=['DELETE'])
@jwt_required()
@limiter.limit("30 per hour")
def delete_comment(comment_id: str):
    """
    Deleta comentário próprio.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar ownership
        comment = verify_comment_ownership(comment_id, current_user_id)
        
        # Deletar comentário
        db.session.delete(comment)
        db.session.commit()
        
        log_user_action('comment_delete', current_user_id, 'comment', comment_id,
                       details={'post_id': str(comment.post_id)})
        
        return jsonify({"message": "Comentário deletado com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        log_security_event('comment_delete_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': comment_id})
        return jsonify({"error": "Erro ao deletar comentário"}), 500

@posts_bp.route('/<post_id>/like', methods=['POST'])
@jwt_required()
@limiter.limit("60 per hour")
def toggle_like_post(post_id: str):
    """
    Alterna like/unlike no post com verificações de visibilidade.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar se post existe e é visível
        post = Post.query.get(post_id)
        if not post or not check_post_visibility(post, current_user_id):
            abort(404)
        
        # Verificar se já curtiu
        existing_like = Like.query.filter_by(
            post_id=post_id,
            user_id=current_user_id
        ).first()
        
        if existing_like:
            # Remover like
            db.session.delete(existing_like)
            db.session.commit()
            
            log_user_action('post_unlike', current_user_id, 'post', post_id)
            
            return jsonify({
                "message": "Like removido com sucesso",
                "liked": False,
                "likes_count": Like.query.filter_by(post_id=post_id).count()
            })
        else:
            # Adicionar like
            like = Like(
                post_id=post_id,
                user_id=current_user_id
            )
            
            db.session.add(like)
            db.session.commit()
            
            log_user_action('post_like', current_user_id, 'post', post_id)
            
            return jsonify({
                "message": "Post curtido com sucesso",
                "liked": True,
                "likes_count": Like.query.filter_by(post_id=post_id).count()
            })
        
    except Exception as e:
        db.session.rollback()
        log_security_event('like_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': post_id})
        return jsonify({"error": "Erro ao curtir post"}), 500

@posts_bp.route('/<post_id>/comment', methods=['POST'])
@jwt_required()
@limiter.limit("30 per hour")
def add_comment(post_id: str):
    """
    Adiciona comentário ao post.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.is_banned:
            abort(404)
        
        # Verificar se post existe e é visível
        post = Post.query.get(post_id)
        if not post or not check_post_visibility(post, current_user_id):
            abort(404)
        
        # Validar campos
        data = request.get_json()
        if not data or not data.get('content'):
            return jsonify({"error": "Conteúdo do comentário é obrigatório"}), 400
        
        content = data['content'].strip()
        if not content:
            return jsonify({"error": "Conteúdo do comentário é obrigatório"}), 400
        
        # Sanitizar conteúdo
        content = sanitize_input(content)
        if len(content) > 1000:
            return jsonify({"error": "Comentário muito longo (máximo 1000 caracteres)"}), 400
        
        # Criar comentário
        comment = Comment(
            post_id=post_id,
            user_id=current_user_id,
            content=content
        )
        
        db.session.add(comment)
        db.session.commit()
        
        log_user_action('comment_create', current_user_id, 'comment', str(comment.id),
                       details={'post_id': post_id})
        
        return jsonify({
            "message": "Comentário criado com sucesso",
            "comment": {
                "id": str(comment.id),
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "author": {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url
                }
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        log_security_event('comment_create_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': post_id})
        return jsonify({"error": "Erro ao criar comentário"}), 500

@posts_bp.route('/<post_id>/comments', methods=['GET'])
@jwt_required()
def get_comments(post_id: str):
    """
    Lista comentários do post com paginação.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar se post existe e é visível
        post = Post.query.get(post_id)
        if not post or not check_post_visibility(post, current_user_id):
            abort(404)
        
        # Validação de paginação
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 20)
        
        # Buscar comentários
        comments_query = Comment.query.filter_by(post_id=post_id).order_by(desc(Comment.created_at))
        comments = comments_query.offset((page - 1) * limit).limit(limit).all()
        total = comments_query.count()
        
        results = []
        for comment in comments:
            # Verificar se autor do comentário está bloqueado
            if not check_block_relationship(current_user_id, str(comment.user_id)):
                results.append({
                    "id": str(comment.id),
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat(),
                    "author": {
                        "id": str(comment.author.id),
                        "username": comment.author.username,
                        "avatar_url": comment.author.avatar_url
                    }
                })
        
        return jsonify({
            "comments": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('comments_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': post_id})
        return jsonify({"error": "Erro ao buscar comentários"}), 500

@posts_bp.route('/<post_id>/comments', methods=['POST'])
@jwt_required()
@limiter.limit("30 per hour")
def create_comment(post_id: str):
    """
    Cria comentário no post.
    """
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.is_banned:
            abort(404)
        
        # Verificar se post existe e é visível
        post = Post.query.get(post_id)
        if not post or not check_post_visibility(post, current_user_id):
            abort(404)
        
        # Validar campos
        data, errors = validate_endpoint_fields('comment_create', request.get_json())
        if errors:
            return jsonify({"error": "Dados inválidos", "details": errors}), 400
        
        content = data['content'].strip()
        if not content:
            return jsonify({"error": "Conteúdo do comentário é obrigatório"}), 400
        
        # Sanitizar conteúdo
        content = sanitize_input(content)
        if len(content) > 1000:
            return jsonify({"error": "Comentário muito longo (máximo 1000 caracteres)"}), 400
        
        # Criar comentário
        comment = Comment(
            post_id=post_id,
            user_id=current_user_id,
            content=content
        )
        
        db.session.add(comment)
        db.session.commit()
        
        log_user_action('comment_create', current_user_id, 'comment', str(comment.id),
                       details={'post_id': post_id})
        
        return jsonify({
            "message": "Comentário criado com sucesso",
            "comment": {
                "id": str(comment.id),
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "author": {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url
                }
            }
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        log_security_event('comment_create_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': post_id})
        return jsonify({"error": "Erro ao criar comentário"}), 500

@posts_bp.route('/user/<user_id>', methods=['GET'])
@jwt_required()
def get_user_posts(user_id: str):
    """
    Obtém posts de um usuário específico com verificações de visibilidade.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar se usuário existe
        user = User.query.get(user_id)
        if not user or user.is_banned:
            abort(404)
        
        # Validação de paginação
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 20)
        
        # Query base para posts do usuário
        posts_query = Post.query.filter_by(user_id=user_id).order_by(desc(Post.created_at))
        
        # Verificar se pode ver os posts
        can_view = False
        if current_user_id == user_id:
            # Próprio usuário
            can_view = True
        elif not user.is_private:
            # Perfil público
            can_view = True
        else:
            # Perfil privado - verificar se segue
            follow = Follow.query.filter_by(
                follower_id=current_user_id,
                following_id=user_id,
                status='accepted'
            ).first()
            can_view = follow is not None
        
        if not can_view:
            return jsonify({
                "error": "Não é possível ver os posts deste usuário",
                "posts": [],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "pages": 0
                }
            }), 403
        
        # Paginação
        posts = posts_query.offset((page - 1) * limit).limit(limit).all()
        total = posts_query.count()
        
        results = []
        for post in posts:
            # Contar likes
            likes_count = Like.query.filter_by(post_id=str(post.id)).count()
            
            # Verificar se usuário curtiu
            is_liked = Like.query.filter_by(
                post_id=str(post.id),
                user_id=current_user_id
            ).first() is not None
            
            # Contar comentários
            comments_count = Comment.query.filter_by(post_id=str(post.id)).count()
            
            results.append({
                "id": str(post.id),
                "user_id": str(post.user_id),
                "content": post.content,
                "media_url": post.media_url,
                "created_at": post.created_at.isoformat(),
                "likes_count": likes_count,
                "comments_count": comments_count,
                "is_liked": is_liked,
                "author": {
                    "id": str(post.author.id),
                    "username": post.author.username,
                    "avatar_url": post.author.avatar_url,
                    "is_private": post.author.is_private
                }
            })
        
        return jsonify({
            "posts": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('user_posts_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_user_id': user_id})
        return jsonify({"error": "Erro ao carregar posts do usuário"}), 500

@posts_bp.route('/feed', methods=['GET'])
@jwt_required()
def get_feed():
    """
    Feed cronológico reverso respeitando bloqueios e privacidade.
    """
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            abort(404)
        
        # Validação de paginação
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 20)
        
        # Query base para o feed
        feed_query = Post.query.join(User, Post.user_id == User.id).filter(
            User.is_banned == False
        )
        
        # Subquery para usuários bloqueados
        blocked_users = db.session.query(Block.blocked_id).filter_by(
            blocker_id=current_user_id
        ).union(
            db.session.query(Block.blocker_id).filter_by(
                blocked_id=current_user_id
            )
        ).subquery()
        
        # Subquery para usuários que segue
        followed_users = db.session.query(Follow.following_id).filter_by(
            follower_id=current_user_id,
            status='accepted'
        ).subquery()
        
        # Filtrar posts: não bloqueados + (públicos ou de usuários seguidos ou próprios)
        feed_query = feed_query.filter(
            and_(
                ~Post.user_id.in_(blocked_users),
                or_(
                    Post.user_id == current_user_id,
                    User.is_private == False,
                    Post.user_id.in_(followed_users)
                )
            )
        )
        
        # Ordenação cronológica reversa
        feed_query = feed_query.order_by(desc(Post.created_at))
        
        # Paginação
        posts = feed_query.offset((page - 1) * limit).limit(limit).all()
        total = feed_query.count()
        
        results = []
        for post in posts:
            # Contar likes
            likes_count = Like.query.filter_by(post_id=str(post.id)).count()
            
            # Verificar se usuário curtiu
            is_liked = Like.query.filter_by(
                post_id=str(post.id),
                user_id=current_user_id
            ).first() is not None
            
            # Contar comentários
            comments_count = Comment.query.filter_by(post_id=str(post.id)).count()
            
            # Carregar comentários recentes (últimos 2)
            recent_comments = Comment.query.filter_by(post_id=str(post.id)).order_by(desc(Comment.created_at)).limit(2).all()
            comments_data = []
            for comment in recent_comments:
                # Verificar se autor do comentário está bloqueado
                if not check_block_relationship(current_user_id, str(comment.user_id)):
                    comments_data.append({
                        "id": str(comment.id),
                        "content": comment.content,
                        "created_at": comment.created_at.isoformat(),
                        "author": {
                            "id": str(comment.author.id),
                            "username": comment.author.username,
                            "avatar_url": comment.author.avatar_url
                        }
                    })
            
            # Verificar se pode ver o post (dupla verificação)
            if check_post_visibility(post, current_user_id):
                results.append({
                    "id": str(post.id),
                    "user_id": str(post.user_id),
                    "content": post.content,
                    "media_url": post.media_url,
                    "created_at": post.created_at.isoformat(),
                    "likes_count": likes_count,
                    "comments_count": comments_count,
                    "is_liked": is_liked,
                    "comments": comments_data,
                    "author": {
                        "id": str(post.author.id),
                        "username": post.author.username,
                        "avatar_url": post.author.avatar_url,
                        "is_private": post.author.is_private
                    }
                })
        
        return jsonify({
            "posts": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('feed_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao carregar feed"}), 500

@posts_bp.route('/<post_id>/report', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def report_post(post_id: str):
    """
    Denuncia post.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar se post existe e é visível
        post = Post.query.get(post_id)
        if not post or not check_post_visibility(post, current_user_id):
            abort(404)
        
        # Validar campos
        data, errors = validate_endpoint_fields('report_create', request.get_json())
        if errors:
            return jsonify({"error": "Dados inválidos", "details": errors}), 400
        
        reason = data['reason'].strip()
        if not reason:
            return jsonify({"error": "Motivo da denúncia é obrigatório"}), 400
        
        if len(reason) > 500:
            return jsonify({"error": "Motivo muito longo (máximo 500 caracteres)"}), 400
        
        # Verificar se já denunciou
        existing_report = Report.query.filter_by(
            reporter_id=current_user_id,
            target_type='post',
            target_id=post_id
        ).first()
        
        if existing_report:
            return jsonify({"error": "Post já denunciado"}), 400
        
        # Criar denúncia
        report = Report(
            reporter_id=current_user_id,
            target_type='post',
            target_id=post_id,
            reason=reason
        )
        
        db.session.add(report)
        db.session.commit()
        
        log_user_action('post_report', current_user_id, 'post', post_id,
                       details={'reason': reason})
        
        return jsonify({"message": "Post denunciado com sucesso"})
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        log_security_event('report_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': post_id})
        return jsonify({"error": "Erro ao denunciar post"}), 500
