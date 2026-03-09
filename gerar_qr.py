import pyotp
import qrcode
from PIL import Image

# Secret do admin
secret = 'TQ7RZV6F4IROBCEVJI6ODJBUDQM7LPJK'
email = 'admin@instaloop.com'
issuer = 'InstaLoop'

# Gerar URI do TOTP
totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
    name=email,
    issuer_name=issuer
)

print(f'URI: {totp_uri}')
print()

# Gerar QR Code
qr = qrcode.QRCode(version=1, box_size=10, border=5)
qr.add_data(totp_uri)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save('/home/whoisgean/InstaLoop/admin_totp_qr.png')
print('QR Code salvo como: admin_totp_qr.png')
print()
print('Para adicionar no Google Authenticator:')
print('1. Abra o Google Authenticator')
print('2. Toque em "+" (adicionar)')
print('3. Escolha "Escanear código QR"')
print('4. Escaneie o arquivo admin_totp_qr.png')
