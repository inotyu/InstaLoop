import os
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import current_app
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'localhost')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@instaloop.local')
        self.from_name = os.getenv('FROM_NAME', 'InstaLoop')
        self.base_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')

    def generate_reset_token(self):
        """Gera token seguro para reset de senha."""
        return secrets.token_urlsafe(32)

    def hash_token(self, token):
        """Hash do token para armazenar no banco."""
        return hashlib.sha256(token.encode()).hexdigest()

    def send_reset_email(self, user_email, reset_token):
        """Envia email de reset de senha de forma segura."""
        try:
            # Criar link de reset
            reset_link = f"{self.base_url}/reset-password?token={reset_token}"
            
            # Conteúdo do email (HTML e texto)
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Recuperação de Senha - InstaLoop</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #4f46e5; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background: #f9fafb; }}
                    .button {{ display: inline-block; padding: 12px 24px; background: #4f46e5; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                    .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                    .warning {{ background: #fef3c7; border: 1px solid #f59e0b; padding: 10px; border-radius: 4px; margin: 15px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔐 InstaLoop</h1>
                        <p>Recuperação de Senha</p>
                    </div>
                    <div class="content">
                        <p>Olá,</p>
                        <p>Recebemos uma solicitação para redefinir sua senha. Se você não fez esta solicitação, ignore este email.</p>
                        
                        <div class="warning">
                            <strong>⚠️ Importante:</strong> Este link expira em 15 minutos e só pode ser usado uma vez.
                        </div>
                        
                        <p>Para redefinir sua senha, clique no botão abaixo:</p>
                        
                        <div style="text-align: center;">
                            <a href="{reset_link}" class="button">Redefinir Senha</a>
                        </div>
                        
                        <p>Ou copie e cole este link no seu navegador:</p>
                        <p style="word-break: break-all; background: #e5e7eb; padding: 10px; border-radius: 4px;">
                            {reset_link}
                        </p>
                        
                        <p><strong>Nunca compartilhe este link com ninguém!</strong></p>
                    </div>
                    <div class="footer">
                        <p>Este é um email automático do InstaLoop. Não responda a este email.</p>
                        <p>Se você não solicitou a redefinição, sua conta permanece segura.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"""
            InstaLoop - Recuperação de Senha
            
            Olá,
            
            Recebemos uma solicitação para redefinir sua senha. Se você não fez esta solicitação, ignore este email.
            
            Link para redefinir sua senha (válido por 15 minutos):
            {reset_link}
            
            ⚠️ Importante:
            - Este link expira em 15 minutos
            - Só pode ser usado uma vez
            - Nunca compartilhe este link com ninguém
            
            Se você não solicitou a redefinição, sua conta permanece segura.
            
            ---
            InstaLoop - Mini Rede Social Segura
            """
            
            # Criar mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Redefinição de Senha - InstaLoop'
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = user_email
            
            # Adicionar conteúdo
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # Enviar email
            if self.smtp_server and self.smtp_username:
                # Configuração SMTP real
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    if self.smtp_use_tls:
                        server.starttls()
                    if self.smtp_password:
                        server.login(self.smtp_username, self.smtp_password)
                    
                    server.send_message(msg)
            else:
                # Modo desenvolvimento - salvar em log
                current_app.logger.info(f"EMAIL DEV MODE: To: {user_email}")
                current_app.logger.info(f"EMAIL DEV MODE: Subject: {msg['Subject']}")
                current_app.logger.info(f"EMAIL DEV MODE: Reset Link: {reset_link}")
            
            # Log de auditoria (desativado temporariamente)
            print(f"Password reset email sent to: {user_email[:10]}***")
            
            return True
            
        except Exception as e:
            print(f"Email send error: {str(e)}")
            return False

    def validate_reset_token(self, token_hash, user_id):
        """Valida token de reset de senha."""
        from models import PasswordReset
        
        # Buscar token não usado
        reset = PasswordReset.query.filter_by(
            token_hash=token_hash,
            user_id=user_id,
            used=False
        ).first()
        
        if not reset:
            return False, "Token inválido ou já usado"
        
        # Verificar expiração
        if datetime.utcnow() > reset.expires_at:
            return False, "Token expirado"
        
        return True, reset

    def mark_token_used(self, reset):
        """Marca token como usado."""
        reset.used = True
        from extensions import db
        db.session.commit()


# Instância global
email_service = EmailService()
