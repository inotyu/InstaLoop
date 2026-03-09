import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import request, g
from utils.security import get_client_ip
from utils.fingerprint import generate_fingerprint
from models import AuditLog
from extensions import db

# Níveis de log
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50
}

# Eventos que devem ser auditados
AUDIT_EVENTS = {
    # Autenticação
    'login_attempt',
    'login_success',
    'login_failed',
    'login_locked',
    'logout',
    'register_attempt',
    'register_success',
    'register_failed',
    'password_reset_request',
    'password_reset_success',
    'password_reset_failed',
    'password_change',
    '2fa_enabled',
    '2fa_disabled',
    '2fa_verify_success',
    '2fa_verify_failed',
    
    # Usuários
    'profile_update',
    'profile_view',
    'avatar_upload',
    'privacy_change',
    'user_blocked',
    'user_unblocked',
    'user_follow',
    'user_unfollow',
    'user_report',
    
    # Posts
    'post_create',
    'post_update',
    'post_delete',
    'post_view',
    'post_like',
    'post_unlike',
    'post_report',
    
    # Comentários
    'comment_create',
    'comment_update',
    'comment_delete',
    'comment_report',
    
    # Mensagens
    'message_send',
    'message_view',
    'message_delete',
    
    # Admin
    'admin_login',
    'admin_action',
    'admin_user_ban',
    'admin_user_unban',
    'admin_report_review',
    'admin_system_change',
    
    # Segurança
    'jwt_invalid',
    'jwt_expired',
    'jwt_manipulated',
    'csrf_invalid',
    'rate_limit_exceeded',
    'suspicious_activity',
    'honeypot_access',
    'devtools_detected',
    'bot_detected',
    'enumeration_attempt',
    'injection_attempt',
    'file_upload_blocked',
    'parameter_pollution',
    
    # Sistema
    'system_error',
    'database_error',
    'service_unavailable'
}

class AuditLogger:
    """
    Logger estruturado para auditoria de segurança.
    """
    
    @staticmethod
    def log_event(
        event: str,
        level: str = 'INFO',
        user_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        resultado: str = 'success',
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        fingerprint: Optional[str] = None
    ) -> bool:
        """
        Registra evento de auditoria no banco de dados.
        """
        try:
            # Validar nível
            if level not in LOG_LEVELS:
                level = 'INFO'
            
            # Validar evento
            if event not in AUDIT_EVENTS:
                event = 'unknown_event'
            
            # Coletar informações do request se não fornecidas
            if request:
                if not ip_address:
                    ip_address = get_client_ip(request)
                if not user_agent:
                    user_agent = request.headers.get('User-Agent', '')[:500]
                if not fingerprint:
                    fingerprint = generate_fingerprint(request)
            
            # Sanitizar detalhes para remover informação sensível
            sanitized_details = AuditLogger._sanitize_details(details or {})
            
            # Criar entrada de log
            audit_log = AuditLog(
                user_id=user_id,
                action=event,
                target_type=target_type,
                target_id=target_id,
                ip=ip_address,
                fingerprint=fingerprint,
                user_agent=user_agent,
                resultado=resultado,
                details_json=sanitized_details,
                timestamp=datetime.utcnow()
            )
            
            # Salvar no banco
            db.session.add(audit_log)
            db.session.commit()
            
            # Para eventos críticos, também logar em arquivo (se configurado)
            if LOG_LEVELS.get(level, 0) >= LOG_LEVELS['WARNING']:
                AuditLogger._log_to_file(event, level, audit_log)
            
            return True
            
        except Exception as e:
            # Silenciar erros de logging para não afetar a aplicação
            db.session.rollback()
            return False
    
    @staticmethod
    def _sanitize_details(details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove informação sensível dos detalhes do log.
        """
        if not isinstance(details, dict):
            return {}
        
        sanitized = {}
        sensitive_keys = {
            'password', 'token', 'secret', 'key', 'hash', 'credit_card',
            'ssn', 'social_security', 'bank_account', 'cvv', 'pin'
        }
        
        for key, value in details.items():
            key_lower = key.lower()
            
            # Verificar se chave é sensível
            is_sensitive = any(sensitive in key_lower for sensitive in sensitive_keys)
            
            if is_sensitive:
                # Para campos sensíveis, manter apenas tipo e tamanho
                if isinstance(value, str):
                    sanitized[key] = f"[REDACTED:{len(value)}]"
                else:
                    sanitized[key] = "[REDACTED]"
            else:
                # Para valores grandes, truncar
                if isinstance(value, str) and len(value) > 1000:
                    sanitized[key] = value[:1000] + "...[TRUNCATED]"
                elif isinstance(value, dict):
                    sanitized[key] = AuditLogger._sanitize_details(value)
                else:
                    sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def _log_to_file(event: str, level: str, audit_log):
        """
        Log adicional em arquivo para eventos críticos.
        """
        try:
            log_entry = {
                "timestamp": audit_log.timestamp.isoformat() + "Z",
                "level": level,
                "event": event,
                "user_id": str(audit_log.user_id) if audit_log.user_id else None,
                "ip": audit_log.ip,
                "ip_subnet": audit_log.ip[:audit_log.ip.rfind('.')] + '.0' if audit_log.ip and '.' in audit_log.ip else None,
                "fingerprint": audit_log.fingerprint,
                "user_agent": audit_log.user_agent,
                "endpoint": request.path if request else None,
                "method": request.method if request else None,
                "resultado": audit_log.resultado,
                "target_type": audit_log.target_type,
                "target_id": str(audit_log.target_id) if audit_log.target_id else None,
                "details": audit_log.details_json
            }
            
            # Em produção, poderia usar um serviço de logging externo
            # Por agora, apenas imprime (em produção seria configurado para arquivo)
            print(f"AUDIT_LOG: {json.dumps(log_entry, separators=(',', ':'))}")
            
        except Exception:
            pass  # Silenciar erros de logging
    
    @staticmethod
    def get_user_activity_summary(user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Retorna resumo de atividade de um usuário.
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            logs = AuditLog.query.filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp > cutoff_date
            ).all()
            
            # Agrupar por tipo de evento
            event_counts = {}
            for log in logs:
                event = log.action
                event_counts[event] = event_counts.get(event, 0) + 1
            
            # Últimas atividades
            recent_activities = [
                {
                    "timestamp": log.timestamp.isoformat() + "Z",
                    "event": log.action,
                    "resultado": log.resultado,
                    "ip": log.ip
                }
                for log in sorted(logs, key=lambda x: x.timestamp, reverse=True)[:10]
            ]
            
            return {
                "period_days": days,
                "total_activities": len(logs),
                "event_counts": event_counts,
                "recent_activities": recent_activities,
                "unique_ips": len(set(log.ip for log in logs if log.ip)),
                "success_rate": sum(1 for log in logs if log.resultado == 'success') / len(logs) if logs else 0
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def get_security_summary(hours: int = 24) -> Dict[str, Any]:
        """
        Retorna resumo de eventos de segurança.
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            security_events = [
                'login_failed', 'login_locked', 'jwt_invalid', 'jwt_expired',
                'jwt_manipulated', 'csrf_invalid', 'rate_limit_exceeded',
                'suspicious_activity', 'honeypot_access', 'devtools_detected',
                'bot_detected', 'enumeration_attempt', 'injection_attempt'
            ]
            
            logs = AuditLog.query.filter(
                AuditLog.action.in_(security_events),
                AuditLog.timestamp > cutoff_time
            ).all()
            
            # Agrupar por tipo
            event_counts = {}
            for log in logs:
                event = log.action
                event_counts[event] = event_counts.get(event, 0) + 1
            
            # Top IPs suspeitos
            ip_counts = {}
            for log in logs:
                if log.ip:
                    ip_counts[log.ip] = ip_counts.get(log.ip, 0) + 1
            
            top_suspicious_ips = sorted(
                ip_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            # Eventos críticos recentes
            critical_events = [
                {
                    "timestamp": log.timestamp.isoformat() + "Z",
                    "event": log.action,
                    "ip": log.ip,
                    "user_agent": log.user_agent,
                    "details": log.details_json
                }
                for log in sorted(logs, key=lambda x: x.timestamp, reverse=True)[:20]
            ]
            
            return {
                "period_hours": hours,
                "total_security_events": len(logs),
                "event_counts": event_counts,
                "top_suspicious_ips": top_suspicious_ips,
                "unique_ips": len(ip_counts),
                "critical_events": critical_events
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def detect_anomalies(user_id: str, hours: int = 1) -> Dict[str, Any]:
        """
        Detecta anomalias no comportamento do usuário.
        """
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            logs = AuditLog.query.filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp > cutoff_time
            ).all()
            
            anomalies = []
            
            # Muitas falhas de login
            failed_logins = [log for log in logs if log.action == 'login_failed']
            if len(failed_logins) > 5:
                anomalies.append({
                    "type": "multiple_login_failures",
                    "count": len(failed_logins),
                    "severity": "high"
                })
            
            # Mudança de IP/fingerprint
            ips = set(log.ip for log in logs if log.ip)
            fingerprints = set(log.fingerprint for log in logs if log.fingerprint)
            
            if len(ips) > 3:
                anomalies.append({
                    "type": "multiple_ips",
                    "count": len(ips),
                    "severity": "medium"
                })
            
            if len(fingerprints) > 2:
                anomalies.append({
                    "type": "multiple_fingerprints",
                    "count": len(fingerprints),
                    "severity": "high"
                })
            
            # Atividade suspeita
            suspicious_events = [log for log in logs if log.action in [
                'suspicious_activity', 'enumeration_attempt', 'injection_attempt'
            ]]
            
            if suspicious_events:
                anomalies.append({
                    "type": "suspicious_activity",
                    "count": len(suspicious_events),
                    "severity": "critical"
                })
            
            # Taxa de erro alta
            failed_events = [log for log in logs if log.resultado == 'failed']
            if len(logs) > 0 and len(failed_events) / len(logs) > 0.5:
                anomalies.append({
                    "type": "high_failure_rate",
                    "failure_rate": len(failed_events) / len(logs),
                    "severity": "medium"
                })
            
            return {
                "period_hours": hours,
                "total_activities": len(logs),
                "anomalies": anomalies,
                "risk_score": sum(a["severity"].count('critical') * 10 + 
                                a["severity"].count('high') * 5 + 
                                a["severity"].count('medium') * 2 + 
                                a["severity"].count('low') * 1 for a in anomalies)
            }
            
        except Exception as e:
            return {"error": str(e)}

# Funções de conveniência para eventos comuns
def log_auth_event(event_type: str, user_id: str = None, resultado: str = 'success', details: dict = None):
    """Log eventos de autenticação"""
    AuditLogger.log_event(
        event=event_type,
        level='WARNING' if resultado == 'failed' else 'INFO',
        user_id=user_id,
        resultado=resultado,
        details=details
    )

def log_security_event(event_type: str, user_id: str = None, details: dict = None):
    """Log eventos de segurança"""
    AuditLogger.log_event(
        event=event_type,
        level='WARNING',
        user_id=user_id,
        resultado='detected',
        details=details
    )

def log_user_action(action: str, user_id: str, target_type: str = None, target_id: str = None, resultado: str = 'success', details: dict = None):
    """Log ações de usuário"""
    AuditLogger.log_event(
        event=action,
        user_id=user_id,
        target_type=target_type,
        target_id=target_id,
        resultado=resultado,
        details=details
    )

def log_admin_action(action: str, admin_id: str, target_type: str = None, target_id: str = None, details: dict = None):
    """Log ações de administrador"""
    AuditLogger.log_event(
        event=f"admin_{action}",
        level='WARNING',
        user_id=admin_id,
        target_type=target_type,
        target_id=target_id,
        resultado='success',
        details=details
    )
