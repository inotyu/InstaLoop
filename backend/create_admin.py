
import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models import User
from utils.security import hash_password

app = create_app()
with app.app_context():
    # Remover qualquer usuário/admin anterior com mesmo username/email
    deleted_by_username = User.query.filter_by(username="admin").delete()
    deleted_by_email = User.query.filter_by(email="admin@instaloop.com").delete()
    if deleted_by_username or deleted_by_email:
        db.session.commit()
        print(f"Removidos usuários antigos de admin (username/email).")

    # Criar usuário admin “limpo”
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

    print("Usuário admin recriado com sucesso!")
    print(f"Username: admin")
    print(f"Email: admin@instaloop.com")
    print(f"Senha: Admin@123")
