import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models import User
from utils.security import hash_password

app = create_app()
with app.app_context():
    # Buscar usuário admin existente
    admin_user = User.query.filter_by(username="admin").first()
    
    if admin_user:
        # Apenas atualizar a senha
        admin_user.password_hash = hash_password("Admin@123")
        db.session.commit()
        print("Senha do usuário admin atualizada com sucesso!")
        print(f"Username: admin")
        print(f"Email: {admin_user.email}")
        print(f"Nova senha: Admin@123")
    else:
        # Se não existir, criar novo
        admin_user = User(
            username="admin",
            email="admin@instaloop.com",
            password_hash=hash_password("Admin@123"),
            is_admin=True,
            is_private=False,
            bio="Administrador do sistema"
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Usuário admin criado com sucesso!")
        print(f"Username: admin")
        print(f"Email: admin@instaloop.com")
        print(f"Senha: Admin@123")
