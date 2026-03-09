from flask import Blueprint, request, jsonify

from utils.audit import log_security_event

telemetry_bp = Blueprint('telemetry', __name__, url_prefix='/api')

@telemetry_bp.route('/telemetry', methods=['POST'])
def telemetry():
    """Recebe eventos do frontend (devtools, honeypot route etc.) e loga silenciosamente."""
    try:
        payload = request.get_json(silent=True) or {}

        event = str(payload.get('event', 'telemetry')).strip()[:100]

        log_security_event(
            event,
            details={
                'payload': payload,
                'endpoint': request.path,
                'method': request.method,
            }
        )

        return jsonify({"status": "ok"})
    except Exception:
        return jsonify({"status": "ok"})
