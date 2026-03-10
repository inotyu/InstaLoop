import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from extensions import db
from models import User
from utils.security import generate_totp_secret, get_totp_provisioning_uri
import qrcode
from io import BytesIO
import base64

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
        print(f"TOTP Secret: {totp_secret}")
        
        # Gerar QR Code
        provisioning_uri = get_totp_provisioning_uri(
            admin_user.username,
            "InstaLoop Admin",
            totp_secret
        )
        
        print(f"Provisioning URI: {provisioning_uri}")
        
        # Gerar QR Code em base64 para fácil visualização
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        print(f"\nQR Code (base64): data:image/png;base64,{img_str}")
        print("\n📱 Para configurar:")
        print("1. Abra seu app autenticador (Google Authenticator, Authy, etc.)")
        print("2. Escaneie o QR code ou digite o secret manualmente")
        print("3. Use o código gerado para acessar o painel admin")
        
    else:
        print("❌ Usuário admin não encontrado!")
