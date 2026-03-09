from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_, desc, func, case, text
from datetime import datetime

from models import Message, User, Block, Follow
from extensions import db
from utils.security import sanitize_input
from utils.validators import validate_pagination_params, ValidationError
from utils.image_processor import process_upload, validate_image_file
from utils.audit import log_user_action, log_security_event
from extensions import limiter

messages_bp = Blueprint('messages', __name__, url_prefix='/api/messages')

def verify_message_access(message_id: str, user_id: str = None):
    """
    Verifica se usuário tem acesso à mensagem (sender ou receiver).
    """
    if user_id is None:
        user_id = get_jwt_identity()
    
    message = Message.query.get(message_id)
    if not message:
        abort(404)
    
    # Verificar se usuário é sender ou receiver
    if str(message.sender_id) != user_id and str(message.receiver_id) != user_id:
        abort(404)  # IDOR protection
    
    return message

def check_message_permission(sender_id: str, receiver_id: str) -> bool:
    """
    Verifica se usuários podem trocar mensagens.
    """
    # Não pode enviar para si mesmo
    if sender_id == receiver_id:
        return False
    
    # Verificar se há bloqueio
    block = Block.query.filter(
        or_(
            and_(Block.blocker_id == sender_id, Block.blocked_id == receiver_id),
            and_(Block.blocker_id == receiver_id, Block.blocked_id == sender_id)
        )
    ).first()
    
    if block:
        return False
    
    # Verificar se ambos os usuários existem e não estão banidos
    sender = User.query.get(sender_id)
    receiver = User.query.get(receiver_id)
    
    if not sender or not receiver or sender.is_banned or receiver.is_banned:
        return False
    
    # Verificar follow mútuo (ambos devem se seguir)
    follow_sender_to_receiver = Follow.query.filter_by(
        follower_id=sender_id,
        following_id=receiver_id,
        status='accepted'
    ).first()
    
    follow_receiver_to_sender = Follow.query.filter_by(
        follower_id=receiver_id,
        following_id=sender_id,
        status='accepted'
    ).first()
    
    if not follow_sender_to_receiver or not follow_receiver_to_sender:
        return False
    
    return True

@messages_bp.route('', methods=['POST'])
@jwt_required()
@limiter.limit("60 per hour")
def send_message():
    """
    Envia mensagem para outro usuário.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Obter dados da requisição
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados da requisição são obrigatórios"}), 400
        
        receiver_id = data.get('receiver_id')
        content = data.get('content', '').strip()
        media_url = data.get('media_url')
        
        # Validar que há conteúdo ou mídia
        if not content and not media_url:
            return jsonify({"error": "Mensagem deve ter conteúdo ou mídia"}), 400
        
        # Validar receiver_id
        if not receiver_id:
            return jsonify({"error": "ID do destinatário é obrigatório"}), 400
        
        # Verificar permissão
        if not check_message_permission(current_user_id, receiver_id):
            log_security_event('message_send_blocked', user_id=current_user_id,
                             details={'receiver_id': receiver_id})
            return jsonify({"error": "Não é possível enviar mensagem para este usuário"}), 400
        
        # Sanitizar conteúdo
        if content:
            content = sanitize_input(content)
            if len(content) > 2000:
                return jsonify({"error": "Conteúdo muito longo (máximo 2000 caracteres)"}), 400
        
        # Criar mensagem
        message = Message(
            sender_id=current_user_id,
            receiver_id=receiver_id,
            content=content,
            media_url=media_url
        )
        
        db.session.add(message)
        db.session.commit()
        
        log_user_action('message_send', current_user_id, 'message', str(message.id),
                       details={'receiver_id': receiver_id, 'has_content': bool(content), 'has_media': bool(media_url)})
        
        # Retornar mensagem criada
        sender = User.query.get(current_user_id)
        receiver = User.query.get(receiver_id)
        
        return jsonify({
            "message": "Mensagem enviada com sucesso",
            "message_data": {
                "id": str(message.id),
                "content": message.content,
                "media_url": message.media_url,
                "is_deleted": message.is_deleted,
                "created_at": message.created_at.isoformat(),
                "sender": {
                    "id": str(sender.id),
                    "username": sender.username,
                    "avatar_url": sender.avatar_url
                },
                "receiver": {
                    "id": str(receiver.id),
                    "username": receiver.username,
                    "avatar_url": receiver.avatar_url
                }
            }
        }), 201
        
    except ValidationError as e:
        return jsonify({"error": e.message}), 400
    except Exception as e:
        db.session.rollback()
        log_security_event('message_send_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao enviar mensagem"}), 500

@messages_bp.route('/upload-media', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour")
def upload_message_media():
    """
    Upload de mídia para mensagens.
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
            
            log_user_action('message_media_upload', current_user_id, 'message', current_user_id,
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
        log_security_event('message_media_upload_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro interno do servidor"}), 500

@messages_bp.route('/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    """
    Lista conversas com todos usuários de follow mútuo (mesmo sem mensagens).
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Validação de paginação
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 20)
        
        # Buscar usuários que eu sigo com follow aceito (excluindo self-follows)
        following = Follow.query.filter(
            Follow.follower_id == current_user_id,
            Follow.following_id != current_user_id,  # Excluir self-follows
            Follow.status == 'accepted'
        ).all()
        
        mutual_users = []
        for follow in following:
            # Verificar se há follow mútuo
            reverse_follow = Follow.query.filter_by(
                follower_id=follow.following_id,
                following_id=current_user_id,
                status='accepted'
            ).first()
            
            if reverse_follow:
                # Buscar usuário manualmente
                user = User.query.get(follow.following_id)
                if user:
                    mutual_users.append(user)
        
        # Para cada usuário mútuo, buscar última mensagem (se existir)
        conversations = []
        for user in mutual_users:
            # Buscar última mensagem entre os dois
            last_message = Message.query.filter(
                or_(
                    and_(Message.sender_id == current_user_id, Message.receiver_id == user.id),
                    and_(Message.sender_id == user.id, Message.receiver_id == current_user_id)
                ),
                Message.is_deleted == False
            ).order_by(desc(Message.created_at)).first()
            
            # Contar mensagens não lidas
            unread_count = Message.query.filter_by(
                sender_id=user.id,
                receiver_id=current_user_id,
                is_deleted=False
            ).count()
            
            conversations.append({
                "other_user": {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url
                },
                "last_message": last_message and {
                    "id": str(last_message.id),
                    "content": last_message.content,
                    "media_url": last_message.media_url,
                    "created_at": last_message.created_at.isoformat(),
                    "is_from_me": last_message.sender_id == current_user_id
                },
                "unread_count": unread_count
            })
        
        # Ordenar por última mensagem (mais recente primeiro), ou por username se sem mensagens
        conversations.sort(key=lambda x: (
            x['last_message']['created_at'] if x['last_message'] else '0000-00-00',
            x['other_user']['username']
        ), reverse=True)
        
        # Paginação
        start = (page - 1) * limit
        end = start + limit
        paginated_conversations = conversations[start:end]
        
        return jsonify({
            "conversations": paginated_conversations,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(conversations),
                "pages": (len(conversations) + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('conversations_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao carregar conversas"}), 500

@messages_bp.route('/conversation/<user_id>', methods=['GET'])
@jwt_required()
def get_conversation_messages(user_id: str):
    """
    Lista mensagens de uma conversa específica.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar permissão
        if not check_message_permission(current_user_id, user_id):
            log_security_event('conversation_access_blocked', user_id=current_user_id,
                             details={'target_user_id': user_id})
            abort(404)
        
        # Validação de paginação
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 50)
        
        # Buscar mensagens da conversa
        messages_query = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user_id, Message.receiver_id == user_id),
                and_(Message.sender_id == user_id, Message.receiver_id == current_user_id)
            ),
            Message.is_deleted == False
        ).order_by(desc(Message.created_at))
        
        messages = messages_query.offset((page - 1) * limit).limit(limit).all()
        total = messages_query.count()
        
        # Marcar mensagens como lidas (em um sistema real, teríamos um campo 'read_at')
        # Por agora, vamos apenas retornar as mensagens
        
        results = []
        for message in reversed(messages):  # Ordem cronológica
            results.append({
                "id": str(message.id),
                "content": message.content,
                "media_url": message.media_url,
                "created_at": message.created_at.isoformat(),
                "is_from_me": message.sender_id == current_user_id,
                "sender": {
                    "id": str(message.sender.id),
                    "username": message.sender.username,
                    "avatar_url": message.sender.avatar_url
                }
            })
        
        return jsonify({
            "messages": results,
            "other_user": {
                "id": user_id,
                "username": User.query.get(user_id).username,
                "avatar_url": User.query.get(user_id).avatar_url
            },
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('conversation_messages_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_user_id': user_id})
        return jsonify({"error": "Erro ao carregar mensagens"}), 500

@messages_bp.route('/<message_id>', methods=['GET'])
@jwt_required()
def get_message(message_id: str):
    """
    Obtém mensagem específica.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar acesso
        message = verify_message_access(message_id, current_user_id)
        
        if message.is_deleted:
            return jsonify({"error": "Mensagem foi apagada"}), 404
        
        log_user_action('message_view', current_user_id, 'message', message_id)
        
        return jsonify({
            "id": str(message.id),
            "content": message.content,
            "media_url": message.media_url,
            "is_deleted": message.is_deleted,
            "created_at": message.created_at.isoformat(),
            "sender": {
                "id": str(message.sender.id),
                "username": message.sender.username,
                "avatar_url": message.sender.avatar_url
            },
            "receiver": {
                "id": str(message.receiver.id),
                "username": message.receiver.username,
                "avatar_url": message.receiver.avatar_url
            }
        })
        
    except Exception as e:
        if not isinstance(e, ValidationError):
            log_security_event('message_view_error', user_id=get_jwt_identity(),
                             details={'error': str(e), 'target_id': message_id})
        raise

@messages_bp.route('/<message_id>', methods=['DELETE'])
@jwt_required()
@limiter.limit("30 per hour")
def delete_message(message_id: str):
    """
    Apaga mensagem (soft delete).
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Verificar acesso
        message = verify_message_access(message_id, current_user_id)
        
        # Apenas o sender pode apagar a mensagem
        if str(message.sender_id) != current_user_id:
            log_security_event('message_delete_unauthorized', user_id=current_user_id,
                             details={'message_id': message_id})
            abort(404)
        
        # Soft delete
        message.is_deleted = True
        message.content = "[Mensagem apagada]"
        message.media_url = None
        
        db.session.commit()
        
        log_user_action('message_delete', current_user_id, 'message', message_id)
        
        return jsonify({"message": "Mensagem apagada com sucesso"})
        
    except Exception as e:
        db.session.rollback()
        log_security_event('message_delete_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'target_id': message_id})
        return jsonify({"error": "Erro ao apagar mensagem"}), 500

@messages_bp.route('/search', methods=['GET'])
@jwt_required()
def search_messages():
    """
    Busca mensagens por conteúdo.
    """
    try:
        current_user_id = get_jwt_identity()
        
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify({"error": "Query muito curta (mínimo 2 caracteres)"}), 400
        
        # Validação de paginação
        params, errors = validate_pagination_params(request.args.to_dict())
        if errors:
            return jsonify({"error": "Parâmetros inválidos"}), 400
        
        page = params.get('page', 1)
        limit = params.get('limit', 20)
        
        # Buscar mensagens do usuário
        messages_query = Message.query.filter(
            or_(
                Message.sender_id == current_user_id,
                Message.receiver_id == current_user_id
            ),
            Message.is_deleted == False,
            Message.content.ilike(f'%{query}%')
        ).order_by(desc(Message.created_at))
        
        messages = messages_query.offset((page - 1) * limit).limit(limit).all()
        total = messages_query.count()
        
        results = []
        for message in messages:
            # Verificar se pode ver a mensagem
            other_user_id = message.receiver_id if message.sender_id == current_user_id else message.sender_id
            if check_message_permission(current_user_id, str(other_user_id)):
                results.append({
                    "id": str(message.id),
                    "content": message.content,
                    "media_url": message.media_url,
                    "created_at": message.created_at.isoformat(),
                    "is_from_me": message.sender_id == current_user_id,
                    "other_user": {
                        "id": str(other_user_id),
                        "username": User.query.get(other_user_id).username,
                        "avatar_url": User.query.get(other_user_id).avatar_url
                    }
                })
        
        return jsonify({
            "messages": results,
            "query": query,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        })
        
    except Exception as e:
        log_security_event('message_search_error', user_id=get_jwt_identity(),
                         details={'error': str(e), 'query': request.args.get('q')})
        return jsonify({"error": "Erro na busca de mensagens"}), 500

@messages_bp.route('/unread-count', methods=['GET'])
@jwt_required()
def get_unread_count():
    """
    Contagem de mensagens não lidas.
    """
    try:
        current_user_id = get_jwt_identity()
        
        # Contar mensagens recebidas não apagadas
        # Em um sistema real, teríamos um campo 'read_at'
        # Por agora, vamos contar todas as mensagens recebidas
        unread_count = Message.query.filter_by(
            receiver_id=current_user_id,
            is_deleted=False
        ).count()
        
        return jsonify({
            "unread_count": unread_count
        })
        
    except Exception as e:
        log_security_event('unread_count_error', user_id=get_jwt_identity(),
                         details={'error': str(e)})
        return jsonify({"error": "Erro ao contar mensagens não lidas"}), 500
