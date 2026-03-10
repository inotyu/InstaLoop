import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models import User
from utils.security import generate_totp_secret, get_totp_provisioning_uri

app = create_app()
with app.app_context():
    # Buscar usuário admin
    admin_user = User.query.filter_by(username="admin").first()
    
    if admin_user:
        # Gerar secret TOTP
        totp_secret = generate_totp_secret()
        admin_user.totp_secret = totp_secret
        db.session.commit()
        
        print("✅ 2FA configurado para o admin!")
        print(f"\n📱 DIGITE ESTE SECRET NO SEU APP AUTENTICADOR:")
        print(f"🔑 Secret: {totp_secret}")
        print(f"\nOu escaneie este URI se preferir:")
        provisioning_uri = get_totp_provisioning_uri(
            admin_user.username,
            "InstaLoop Admin",
            totp_secret
        )
        print(f"📷 URI: {provisioning_uri}")
        
        print(f"\n⚠️  IMPORTANTE:")
        print(f"1. Abra seu app autenticador (Google Authenticator, Authy, etc.)")
        print(f"2. Adicione uma nova conta")
        print(f"3. Digite o secret acima manualmente")
        print(f"4. Use o código de 6 dígitos gerado para acessar o painel admin")
        
    else:
        print("❌ Usuário admin não encontrado!")
