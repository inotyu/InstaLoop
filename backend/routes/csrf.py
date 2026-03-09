import os
from flask import Blueprint, jsonify, make_response, current_app

from utils.security import generate_csrf_token

csrf_bp = Blueprint('csrf', __name__, url_prefix='/api')

@csrf_bp.route('/csrf', methods=['GET'])
def issue_csrf():
    """Issue a CSRF token using Double Submit Cookie pattern.

    - Returns token in body
    - Sets the same token in HttpOnly cookie (Strict)
    """
    token = generate_csrf_token()

    response = make_response(jsonify({"csrf_token": token}))
    # Detectar ambiente para configurar SameSite corretamente
    is_vercel = os.environ.get('VERCEL') is not None
    
    response.set_cookie(
        'csrf_token',
        token,
        httponly=True,
        secure=True,  # Sempre secure em produção/vercel
        samesite='None' if is_vercel else ('Lax' if current_app.debug else 'Strict'),
        max_age=60 * 60,  # 1h
        path='/',
        partitioned=is_vercel  # Partitioned para cross-site na Vercel
    )
    return response
