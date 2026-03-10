import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models import User

app = create_app()
with app.app_context():
    # Buscar usuário admin
    admin_user = User.query.filter_by(username="admin").first()
    
    if admin_user:
        # Resetar lockout e tentativas falhas
        admin_user.failed_login_attempts = 0
        admin_user.locked_until = None
        db.session.commit()
        
        print("✅ Usuário admin desbloqueado com sucesso!")
        print(f"Username: {admin_user.username}")
        print(f"Tentativas falhas resetadas: {admin_user.failed_login_attempts}")
        print(f"Locked until: {admin_user.locked_until}")
    else:
        print("❌ Usuário admin não encontrado!")
