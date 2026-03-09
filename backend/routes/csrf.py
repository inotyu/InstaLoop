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
    response.set_cookie(
        'csrf_token',
        token,
        httponly=True,
        secure=not current_app.debug,
        samesite='Strict',
        max_age=60 * 60,  # 1h
        path='/'
    )
    return response
