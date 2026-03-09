#!/bin/bash
source .venv311/bin/activate
python -c "
import pyotp
secret = 'TQ7RZV6F4IROBCEVJI6ODJBUDQM7LPJK'
totp = pyotp.TOTP(secret)
print(f'Código TOTP: {totp.now()}')
"
