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
        print(f"Usuário admin: {admin_user.username}")
        print(f"É admin: {admin_user.is_admin}")
        print(f"Tem TOTP secret: {bool(admin_user.totp_secret)}")
        print(f"TOTP secret: {admin_user.totp_secret}")
        
        if not admin_user.totp_secret:
            print("❌ Admin não tem 2FA configurado!")
            print("Para acessar o painel admin, é necessário configurar 2FA primeiro.")
        else:
            print("✅ Admin tem 2FA configurado!")
    else:
        print("❌ Usuário admin não encontrado!")
