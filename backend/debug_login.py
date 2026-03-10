import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from utils.validators import validate_endpoint_fields

app = create_app()
with app.app_context():
    # Testar validação do login
    raw_json = {'identifier': 'admin', 'password': 'Admin@123'}
    print(f"Testando validação com: {raw_json}")
    
    try:
        data, errors = validate_endpoint_fields('auth_login', raw_json, raw_json)
        print(f"Dados filtrados: {data}")
        print(f"Erros: {errors}")
        
        if errors:
            print("❌ Validação falhou!")
            for error in errors:
                print(f"  - {error}")
        else:
            print("✅ Validação bem-sucedida!")
            
    except Exception as e:
        print(f"❌ Exceção na validação: {e}")
        import traceback
        traceback.print_exc()
