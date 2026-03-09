from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import datetime
import uuid

from models import Report, User, Post, Like, Comment
from extensions import db
from utils.audit import log_security_event

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('', methods=['POST', 'OPTIONS'])
def create_report():
    """Criar nova denúncia"""
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Verificar JWT manualmente
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request()
        reporter_id = get_jwt_identity()
        
        data = request.get_json()
        
        # Validar campos obrigatórios
        if not data.get('target_type') or not data.get('target_id') or not data.get('reason'):
            return jsonify({
                'error': 'Campos obrigatórios: target_type, target_id, reason'
            }), 400
        
        target_type = data['target_type']
        target_id = data['target_id']
        reason = data['reason']
        description = data.get('description', '')
        
        # Verificar se o alvo existe
        if target_type == 'post':
            target = Post.query.get(target_id)
            if not target:
                return jsonify({'error': 'Post não encontrado'}), 404
        elif target_type == 'user':
            target = User.query.get(target_id)
            if not target:
                return jsonify({'error': 'Usuário não encontrado'}), 404
        else:
            return jsonify({'error': 'Tipo de alvo inválido'}), 400
        
        # Verificar se o usuário já denunciou este alvo
        existing_report = Report.query.filter_by(
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id
        ).first()
        
        if existing_report:
            return jsonify({'error': 'Você já denunciou este conteúdo/usuário'}), 400
        
        # Criar denúncia
        report = Report(
            id=str(uuid.uuid4()),
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            description=description,
            status='pending',
            created_at=datetime.datetime.utcnow()
        )
        
        db.session.add(report)
        db.session.commit()
        
        # Log de auditoria
        log_security_event('report_created', 
                          user_id=reporter_id,
                          details={
                              'target_type': target_type,
                              'target_id': target_id,
                              'reason': reason
                          })
        
        return jsonify({
            'message': 'Denúncia criada com sucesso',
            'report_id': report.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao criar denúncia: {e}")
        return jsonify({'error': 'Erro ao criar denúncia'}), 500

@reports_bp.route('', methods=['GET'])
@jwt_required()
def get_reports():
    """Listar denúncias (apenas admin)"""
    try:
        # Verificar se é admin
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error': 'Acesso negado'}), 403
        
        # Parâmetros de paginação
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', 'pending')
        
        # Query base
        query = Report.query
        
        # Filtrar por status se fornecido
        if status != 'all':
            query = query.filter_by(status=status)
        
        # Ordenar por data (mais recentes primeiro)
        query = query.order_by(Report.created_at.desc())
        
        # Paginar
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        reports_data = []
        for report in pagination.items:
            # Buscar informações do reporter
            reporter = User.query.get(report.reporter_id)
            
            # Buscar informações do alvo
            target_info = None
            if report.target_type == 'post':
                target_post = Post.query.get(report.target_id)
                if target_post:
                    target_user = User.query.get(target_post.user_id)
                    target_info = {
                        'id': target_post.id,
                        'content': target_post.content[:100] + '...' if len(target_post.content) > 100 else target_post.content,
                        'author': target_user.username if target_user else 'Desconhecido',
                        'author_id': target_user.id if target_user else None
                    }
            elif report.target_type == 'user':
                target_user = User.query.get(report.target_id)
                if target_user:
                    target_info = {
                        'id': target_user.id,
                        'username': target_user.username,
                        'email': target_user.email
                    }
            
            reports_data.append({
                'id': report.id,
                'target_type': report.target_type,
                'target_info': target_info,
                'reporter': {
                    'id': reporter.id,
                    'username': reporter.username
                } if reporter else None,
                'reason': report.reason,
                'description': report.description,
                'status': report.status,
                'created_at': report.created_at.isoformat(),
                'reviewed_at': report.reviewed_at.isoformat() if report.reviewed_at else None,
                'reviewed_by': report.reviewed_by
            })
        
        return jsonify({
            'data': reports_data,
            'pagination': {
                'page': page,
                'pages': pagination.pages,
                'per_page': per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'error': 'Erro ao buscar denúncias'}), 500

@reports_bp.route('/<report_id>/review', methods=['POST'])
@jwt_required()
def review_report(report_id):
    """Aprovar ou rejeitar denúncia"""
    try:
        # Verificar se é admin
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({'error': 'Acesso negado'}), 403
        
        data = request.get_json()
        status = data.get('status')  # 'approve' ou 'dismiss'
        
        if status not in ['approve', 'dismiss']:
            return jsonify({'error': 'Ação inválida'}), 400
        
        # Buscar denúncia
        report = Report.query.get(report_id)
        if not report:
            return jsonify({'error': 'Denúncia não encontrada'}), 404
        
        if report.status != 'pending':
            return jsonify({'error': 'Denúncia já foi revisada'}), 400
        
        # Atualizar status
        report.status = 'reviewed' if action == 'approve' else 'dismissed'
        report.reviewed_at = datetime.datetime.utcnow()
        report.reviewed_by = current_user_id
        
        # Se aprovou, aplicar ação correspondente
        if action == 'approve':
            if report.target_type == 'post':
                # Excluir post completamente
                target_post = Post.query.get(report.target_id)
                if target_post:
                    # Remover curtidas e comentários relacionados
                    Like.query.filter_by(post_id=report.target_id).delete()
                    Comment.query.filter_by(post_id=report.target_id).delete()
                    
                    # Excluir o post
                    db.session.delete(target_post)
            
            elif report.target_type == 'user':
                # Suspender usuário
                target_user = User.query.get(report.target_id)
                if target_user:
                    target_user.is_banned = True
                    db.session.add(target_user)
        
        db.session.add(report)
        db.session.commit()
        
        # Log de auditoria
        log_security_event('report_reviewed',
                          user_id=current_user_id,
                          details={
                              'report_id': report_id,
                              'action': action,
                              'target_type': report.target_type,
                              'target_id': report.target_id
                          })
        
        return jsonify({
            'message': f'Denúncia {status == "approve" and "aprovada" or "rejeitada"} com sucesso',
            'status': report.status
        })
        
    except Exception as e:
        log_security_event('report_review_error', user_id=current_user_id,
                         details={'error': str(e), 'report_id': report_id})
        db.session.rollback()
        return jsonify({'error': 'Erro ao revisar denúncia'}), 500
