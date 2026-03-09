import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from flask import request
from utils.security import get_client_ip
from utils.fingerprint import generate_fingerprint
from utils.audit import log_security_event
from models import AuditLog, User
from extensions import db

class BehavioralAnalyzer:
    """
    Analisador de comportamento para detecção de bots e atividades suspeitas.
    """
    
    def __init__(self):
        self.thresholds = {
            'max_actions_per_second': 10,
            'max_actions_per_minute': 100,
            'max_same_action_per_second': 5,
            'max_uuid_enumeration_per_minute': 20,
            'max_failed_auth_per_minute': 10,
            'max_requests_per_session': 1000,
            'min_human_typing_delay': 0.1,  # 100ms mínimo entre digitações
            'max_concurrent_sessions': 3,
        }
    
    def detect_automated_behavior(self, user_id: str = None, action: str = None, ip_address: str = None) -> Dict[str, Any]:
        """
        Detecta comportamento automatizado baseado em múltiplos fatores.
        """
        if not ip_address:
            ip_address = get_client_ip(request)
        
        detection_results = {
            'is_automated': False,
            'risk_score': 0,
            'reasons': [],
            'should_block': False,
            'block_duration': None
        }
        
        # 1. Detecção de alta frequência de ações
        freq_result = self._detect_high_frequency_actions(user_id, action)
        if freq_result['detected']:
            detection_results['is_automated'] = True
            detection_results['risk_score'] += freq_result['risk_score']
            detection_results['reasons'].extend(freq_result['reasons'])
        
        # 2. Detecção de enumeração de UUIDs
        enum_result = self._detect_uuid_enumeration(user_id)
        if enum_result['detected']:
            detection_results['is_automated'] = True
            detection_results['risk_score'] += enum_result['risk_score']
            detection_results['reasons'].extend(enum_result['reasons'])
        
        # 3. Detecção de padrões de bot
        pattern_result = self._detect_bot_patterns(ip_address)
        if pattern_result['detected']:
            detection_results['is_automated'] = True
            detection_results['risk_score'] += pattern_result['risk_score']
            detection_results['reasons'].extend(pattern_result['reasons'])
        
        # 4. Detecção de sessões múltiplas
        session_result = self._detect_multiple_sessions(user_id, ip_address)
        if session_result['detected']:
            detection_results['is_automated'] = True
            detection_results['risk_score'] += session_result['risk_score']
            detection_results['reasons'].extend(session_result['reasons'])
        
        # 5. Detecção de timing não humano
        timing_result = self._detect_non_human_timing(user_id)
        if timing_result['detected']:
            detection_results['is_automated'] = True
            detection_results['risk_score'] += timing_result['risk_score']
            detection_results['reasons'].extend(timing_result['reasons'])
        
        # Decisão de bloqueio
        if detection_results['risk_score'] >= 50:
            detection_results['should_block'] = True
            detection_results['block_duration'] = min(detection_results['risk_score'] // 10, 24)  # horas
        
        # Log de detecção
        if detection_results['is_automated']:
            log_security_event(
                'bot_detected',
                user_id=user_id,
                details={
                    'risk_score': detection_results['risk_score'],
                    'reasons': detection_results['reasons'],
                    'ip_address': ip_address,
                    'action': action
                }
            )
        
        return detection_results
    
    def _detect_high_frequency_actions(self, user_id: str = None, action: str = None) -> Dict[str, Any]:
        """
        Detecta ações em frequência não humana.
        """
        result = {'detected': False, 'risk_score': 0, 'reasons': []}
        
        try:
            # Ações no último segundo
            one_second_ago = datetime.utcnow() - timedelta(seconds=1)
            recent_actions = AuditLog.query.filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp > one_second_ago
            ).count()
            
            if recent_actions > self.thresholds['max_actions_per_second']:
                result['detected'] = True
                result['risk_score'] += 30
                result['reasons'].append(f'mais_de {self.thresholds["max_actions_per_second"]} ações no último segundo')
            
            # Ações no último minuto
            one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
            recent_minute_actions = AuditLog.query.filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp > one_minute_ago
            ).count()
            
            if recent_minute_actions > self.thresholds['max_actions_per_minute']:
                result['detected'] = True
                result['risk_score'] += 20
                result['reasons'].append(f'mais de {self.thresholds["max_actions_per_minute"]} ações no último minuto')
            
            # Mesma ação repetida
            if action:
                same_action_count = AuditLog.query.filter(
                    AuditLog.user_id == user_id,
                    AuditLog.action == action,
                    AuditLog.timestamp > one_second_ago
                ).count()
                
                if same_action_count > self.thresholds['max_same_action_per_second']:
                    result['detected'] = True
                    result['risk_score'] += 25
                    result['reasons'].append(f'mais de {self.thresholds["max_same_action_per_second"]} ações "{action}" no último segundo')
            
        except Exception:
            pass
        
        return result
    
    def _detect_uuid_enumeration(self, user_id: str = None) -> Dict[str, Any]:
        """
        Detecta padrão de enumeração de UUIDs (tentativa de encontrar recursos válidos).
        """
        result = {'detected': False, 'risk_score': 0, 'reasons': []}
        
        try:
            # Verificar tentativas de acesso a recursos não encontrados
            five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
            
            not_found_logs = AuditLog.query.filter(
                AuditLog.user_id == user_id,
                AuditLog.resultado == 'not_found',
                AuditLog.timestamp > five_minutes_ago
            ).all()
            
            if len(not_found_logs) > self.thresholds['max_uuid_enumeration_per_minute']:
                result['detected'] = True
                result['risk_score'] += 40
                result['reasons'].append(f'mais de {self.thresholds["max_uuid_enumeration_per_minute"]} recursos não encontrados em 5 minutos')
                
                # Analisar padrão dos UUIDs tentados
                uuid_patterns = self._analyze_uuid_patterns(not_found_logs)
                if uuid_patterns['is_sequential']:
                    result['risk_score'] += 20
                    result['reasons'].append('padrão sequencial detectado nos UUIDs tentados')
            
        except Exception:
            pass
        
        return result
    
    def _analyze_uuid_patterns(self, logs: List[AuditLog]) -> Dict[str, Any]:
        """
        Analisa padrões nos UUIDs para detectar enumeração.
        """
        try:
            uuids = [log.target_id for log in logs if log.target_id]
            
            if len(uuids) < 5:
                return {'is_sequential': False}
            
            # Verificar se os UUIDs têm padrão (primeiros caracteres iguais)
            prefixes = {}
            for uid in uuids:
                if uid:
                    prefix = uid[:8]  # Primeiros 8 caracteres
                    prefixes[prefix] = prefixes.get(prefix, 0) + 1
            
            # Se muitos UUIDs compartilham o mesmo prefixo, pode ser enumeração
            max_prefix_count = max(prefixes.values()) if prefixes else 0
            if max_prefix_count > len(uuids) * 0.7:  # 70% com mesmo prefixo
                return {'is_sequential': True}
            
            return {'is_sequential': False}
            
        except Exception:
            return {'is_sequential': False}
    
    def _detect_bot_patterns(self, ip_address: str) -> Dict[str, Any]:
        """
        Detecta padrões típicos de bots baseados em User-Agent e headers.
        """
        result = {'detected': False, 'risk_score': 0, 'reasons': []}
        
        try:
            user_agent = request.headers.get('User-Agent', '').lower()
            
            # User-Agents suspeitos
            bot_agents = [
                'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
                'python-requests', 'powershell', 'bash', 'java', 'node',
                'go-http', 'rust', 'axios', 'httpie', 'postman',
                'insomnia', 'swagger', 'sqlmap', 'nikto', 'nmap'
            ]
            
            for agent in bot_agents:
                if agent in user_agent:
                    result['detected'] = True
                    result['risk_score'] += 15
                    result['reasons'].append(f'User-Agent suspeito: {agent}')
                    break
            
            # Headers ausentes em browsers normais
            normal_headers = ['accept', 'accept-language', 'accept-encoding']
            missing_headers = [h for h in normal_headers if not request.headers.get(h)]
            
            if len(missing_headers) >= 2:
                result['detected'] = True
                result['risk_score'] += 10
                result['reasons'].append(f'Headers ausentes: {missing_headers}')
            
            # Headers de automação
            automation_headers = ['x-automation', 'x-bot', 'x-crawler']
            for header in automation_headers:
                if request.headers.get(header):
                    result['detected'] = True
                    result['risk_score'] += 20
                    result['reasons'].append(f'Header de automação detectado: {header}')
            
            # Timing consistente (muito rápido)
            if hasattr(request, 'start_time'):
                request_time = time.time() - request.start_time
                if request_time < 0.01:  # Menos de 10ms é suspeito
                    result['detected'] = True
                    result['risk_score'] += 10
                    result['reasons'].append('tempo de request suspeitamente rápido')
            
        except Exception:
            pass
        
        return result
    
    def _detect_multiple_sessions(self, user_id: str = None, ip_address: str = None) -> Dict[str, Any]:
        """
        Detecta múltiplas sessões simultâneas do mesmo usuário.
        """
        result = {'detected': False, 'risk_score': 0, 'reasons': []}
        
        try:
            if not user_id:
                return result
            
            # Contar fingerprints únicos nas últimas 24h
            one_day_ago = datetime.utcnow() - timedelta(hours=24)
            
            unique_fingerprints = db.session.query(
                AuditLog.fingerprint
            ).filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp > one_day_ago,
                AuditLog.fingerprint.isnot(None)
            ).distinct().count()
            
            if unique_fingerprints > self.thresholds['max_concurrent_sessions']:
                result['detected'] = True
                result['risk_score'] += 15
                result['reasons'].append(f'{unique_fingerprints} fingerprints únicos em 24h')
            
            # IPs diferentes em curto período
            unique_ips = db.session.query(
                AuditLog.ip
            ).filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp > one_day_ago,
                AuditLog.ip.isnot(None)
            ).distinct().count()
            
            if unique_ips > 5:
                result['detected'] = True
                result['risk_score'] += 20
                result['reasons'].append(f'{unique_ips} IPs diferentes em 24h')
            
        except Exception:
            pass
        
        return result
    
    def _detect_non_human_timing(self, user_id: str = None) -> Dict[str, Any]:
        """
        Detecta padrões de timing não humanos.
        """
        result = {'detected': False, 'risk_score': 0, 'reasons': []}
        
        try:
            if not user_id:
                return result
            
            # Analisar intervalos entre ações do mesmo tipo
            recent_logs = AuditLog.query.filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp > datetime.utcnow() - timedelta(minutes=10)
            ).order_by(AuditLog.timestamp).all()
            
            if len(recent_logs) < 5:
                return result
            
            # Calcular intervalos entre ações consecutivas
            intervals = []
            for i in range(1, len(recent_logs)):
                interval = (recent_logs[i].timestamp - recent_logs[i-1].timestamp).total_seconds()
                intervals.append(interval)
            
            # Verificar se intervalos são muito consistentes (característico de bots)
            if len(intervals) >= 5:
                avg_interval = sum(intervals) / len(intervals)
                variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
                std_dev = variance ** 0.5
                
                # Baixo desvio padrão indica timing robótico
                if std_dev < 0.1 and avg_interval < 1.0:
                    result['detected'] = True
                    result['risk_score'] += 25
                    result['reasons'].append('timing excessivamente consistente (possível bot)')
            
            # Verificar intervalos muito curtos
            very_short_intervals = [i for i in intervals if i < self.thresholds['min_human_typing_delay']]
            if len(very_short_intervals) > len(intervals) * 0.5:
                result['detected'] = True
                result['risk_score'] += 20
                result['reasons'].append('intervalos muito curtos entre ações')
            
        except Exception:
            pass
        
        return result
    
    def ban_user_temporarily(self, user_id: str, minutes: int, reason: str = None):
        """
        Bane usuário temporariamente por comportamento suspeito.
        """
        try:
            user = User.query.get(user_id)
            if user:
                user.is_banned = True
                # Em um sistema real, teríamos um campo banned_until
                # Por agora, vamos apenas marcar como banido
                
                db.session.commit()
                
                log_security_event(
                    'user_banned',
                    user_id=user_id,
                    details={
                        'reason': reason or 'comportamento automatizado',
                        'duration_minutes': minutes,
                        'auto_ban': True
                    }
                )
                
                return True
        except Exception:
            pass
        
        return False
    
    def get_user_behavior_profile(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Gera perfil de comportamento do usuário.
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            logs = AuditLog.query.filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp > cutoff_date
            ).order_by(AuditLog.timestamp).all()
            
            if not logs:
                return {'error': 'no_data'}
            
            # Análise temporal
            hourly_activity = {}
            for log in logs:
                hour = log.timestamp.hour
                hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
            
            # Picos de atividade (possíveis bots)
            max_hourly = max(hourly_activity.values()) if hourly_activity else 0
            avg_hourly = sum(hourly_activity.values()) / len(hourly_activity) if hourly_activity else 0
            
            spike_ratio = max_hourly / avg_hourly if avg_hourly > 0 else 0
            
            # Consistência de fingerprint
            fingerprints = set(log.fingerprint for log in logs if log.fingerprint)
            fingerprint_consistency = len(fingerprints) / len(logs) if logs else 0
            
            # Padrões de ação
            action_patterns = {}
            for log in logs:
                action = log.action
                action_patterns[action] = action_patterns.get(action, 0) + 1
            
            # Score de humanidade (quanto mais alto, mais humano)
            humanity_score = 100
            humanity_score -= spike_ratio * 10  # Picos reduzem score
            humanity_score -= (1 - fingerprint_consistency) * 30  # Múltiplos fingerprints reduzem score
            humanity_score = max(0, humanity_score)
            
            return {
                'period_days': days,
                'total_actions': len(logs),
                'unique_fingerprints': len(fingerprints),
                'fingerprint_consistency': fingerprint_consistency,
                'hourly_activity': hourly_activity,
                'activity_spike_ratio': spike_ratio,
                'action_patterns': action_patterns,
                'humanity_score': humanity_score,
                'is_suspicious': humanity_score < 50
            }
            
        except Exception as e:
            return {'error': str(e)}

# Instância global do analisador
behavioral_analyzer = BehavioralAnalyzer()

def detect_automated_behavior(user_id: str = None, action: str = None) -> Dict[str, Any]:
    """
    Função de conveniência para detecção de comportamento automatizado.
    """
    return behavioral_analyzer.detect_automated_behavior(user_id, action)


def get_user_behavior_profile(user_id: str, days: int = 7) -> Dict[str, Any]:
    """Wrapper para gerar perfil comportamental do usuário (usado no admin)."""
    return behavioral_analyzer.get_user_behavior_profile(user_id, days=days)


def banir_temporariamente(user_id: str, minutos: int = 60, reason: str = None) -> bool:
    """Alias em PT-BR para ban temporário (compatibilidade)."""
    return behavioral_analyzer.ban_user_temporarily(user_id, minutes=minutos, reason=reason)

def ban_user_if_bot(user_id: str, detection_result: Dict[str, Any]):
    """
    Bane usuário se detecção indicar comportamento de bot.
    """
    if detection_result['should_block'] and detection_result['block_duration']:
        return behavioral_analyzer.ban_user_temporarily(
            user_id,
            detection_result['block_duration'] * 60,  # converter horas para minutos
            f"Comportamento automatizado detectado: {', '.join(detection_result['reasons'])}"
        )
    return False
