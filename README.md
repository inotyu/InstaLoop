# InstaLoop 🔄

Uma rede social completa e segura com autenticação avançada, painel administrativo e recursos de segurança cibernética.

## 🚀 Visão Geral

InstaLoop é uma plataforma de rede social moderna construída com **Flask** (backend) e **React + Vite** (frontend), utilizando **PostgreSQL** como banco de dados. O projeto inclui recursos avançados de segurança como autenticação em duas etapas (2FA), proteção CSRF, rate limiting, detecção de comportamento automatizado e um painel administrativo secreto.

## 🛠️ Pré-requisitos

Antes de começar, certifique-se de ter instalado:

### Sistema Operacional
- **Linux/macOS** (recomendado) ou **Windows com WSL**
- **Python 3.11+**
- **Node.js 18+** e **npm**
- **PostgreSQL 13+**

### Verificar instalações
```bash
# Python
python3 --version  # Linux/macOS
python --version   # Windows

# Node.js
node --version
npm --version

# PostgreSQL
psql --version
```

### Para Windows (PowerShell/Command Prompt):
```cmd
# Python
python --version

# Node.js  
node --version
npm --version

# PostgreSQL (verificar se está no PATH)
psql --version
```

## 📦 Instalação

### 1. Clonar o repositório
```bash
git clone https://github.com/inotyu/InstaLoop.git
cd InstaLoop
```

### 2. Configurar Banco de Dados PostgreSQL

#### Linux/macOS:
```bash
# Conectar ao PostgreSQL
sudo -u postgres psql

# Dentro do PostgreSQL
CREATE DATABASE instaloop;
CREATE USER instaloop_user WITH PASSWORD 'Darson2';
GRANT ALL PRIVILEGES ON DATABASE instaloop TO instaloop_user;
\q
```

#### Windows (Command Prompt como Administrator):
```cmd
REM Conectar ao PostgreSQL (ajuste o caminho se necessário)
"C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres

REM Dentro do PostgreSQL
CREATE DATABASE instaloop;
CREATE USER instaloop_user WITH PASSWORD 'Darson2';
GRANT ALL PRIVILEGES ON DATABASE instaloop TO instaloop_user;
\q
```

#### Windows (PowerShell como Administrator):
```powershell
# Conectar ao PostgreSQL
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres

# Dentro do PostgreSQL (mesmos comandos SQL acima)
```

#### Configurar conexão
O arquivo `.env` já está configurado para usar:
```env
DATABASE_URL=postgresql://instaloop_user:Darson2@localhost:5432/instaloop
```

### 3. Configurar Backend

#### Linux/macOS:
```bash
# Entrar no diretório backend
cd backend

# Criar ambiente virtual
python3 -m venv .venv311
source .venv311/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

#### Windows (Command Prompt):
```cmd
REM Entrar no diretório backend
cd backend

REM Criar ambiente virtual
python -m venv .venv311

REM Ativar ambiente virtual
.venv311\Scripts\activate

REM Instalar dependências
pip install -r requirements.txt
```

#### Windows (PowerShell):
```powershell
# Entrar no diretório backend
cd backend

# Criar ambiente virtual
python -m venv .venv311

# Ativar ambiente virtual
.\.venv311\Scripts\Activate.ps1

# Instalar dependências
pip install -r requirements.txt
```

#### Verificar instalação (todos os SO):
```bash
python -c "import flask; print('Flask OK')"
python -c "import psycopg2; print('PostgreSQL OK')"
```

### 4. Configurar Frontend

```bash
# Entrar no diretório frontend
cd ../frontend

# Instalar dependências
npm install

# Verificar instalação
npm list react vite
```

## 🚀 Executando o Projeto

### Opção 1: Script Automático (Recomendado)

```bash
# Na raiz do projeto
chmod +x run.sh
./run.sh
```

### Opção 2: Execução Manual

#### Terminal 1: Backend

**Linux/macOS:**
```bash
cd backend
source .venv311/bin/activate
python app.py
```

**Windows (Command Prompt):**
```cmd
cd backend
.venv311\Scripts\activate
python app.py
```

**Windows (PowerShell):**
```powershell
cd backend
.\.venv311\Scripts\Activate.ps1
python app.py
```

**Servidor backend:** http://localhost:5000

#### Terminal 2: Frontend

**Todos os SO:**
```bash
cd frontend
npm run dev
```

**Servidor frontend:** http://localhost:5173

## 🔐 Acesso ao Sistema

### Login de Usuário Normal
- **URL:** http://localhost:5173/login
- Registre-se ou faça login com qualquer conta

## 🚨 Desafio de Segurança - Yuri, pode tentar hackear! 🕵️‍♂️

Este projeto foi desenvolvido com foco em segurança cibernética. Yuri pode tentar descobrir vulnerabilidades e explorar o sistema!

### Logs para Monitorar:
```bash
# Ver logs de segurança
tail -f backend/logs/security.log

# Ver logs de auditoria
tail -f backend/logs/audit.log
```

## 🔧 Troubleshooting

### Erro: "source: arquivo ou diretório inexistente: .venv311/bin/activate"
**Linux/macOS:**
```bash
# Recriar ambiente virtual
cd backend
python3 -m venv .venv311
source .venv311/bin/activate
pip install -r requirements.txt
```

**Windows:**
```cmd
REM Recriar ambiente virtual
cd backend
python -m venv .venv311
.venv311\Scripts\activate
pip install -r requirements.txt
```

### Erro: "psycopg2.errors.ConnectionError"
```bash
# Verificar se PostgreSQL está rodando
sudo systemctl status postgresql  # Linux
# Windows: Verificar serviços do Windows -> PostgreSQL

# Verificar credenciais no .env
cat .env | grep DATABASE_URL      # Linux/macOS
type .env | findstr DATABASE_URL  # Windows
```

### Erro: "ModuleNotFoundError: No module named 'flask'"
```bash
# Instalar dependências novamente
cd backend
source .venv311/bin/activate  # Linux/macOS
# ou
.venv311\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Erro: "404 Not Found" no painel admin
```bash
# Verificar se o admin tem 2FA configurado
cd backend
source .venv311/bin/activate  # Linux/macOS
python check_admin_2fa.py

# Windows
cd backend
.venv311\Scripts\activate
python check_admin_2fa.py

# Se não tiver, configurar
python setup_admin_2fa_simple.py
```

### Frontend não carrega
```bash
# Limpar cache do Vite
cd frontend
rm -rf node_modules/.vite  # Linux/macOS
# ou
rd /s /q node_modules\.vite  # Windows
npm run dev
```

### Database migrations
```bash
# O Flask-SQLAlchemy cria as tabelas automaticamente
# Se precisar recriar, delete o banco e reinicie
```

## 📊 Estrutura do Projeto

```
InstaLoop/
├── backend/                 # API Flask
│   ├── app.py              # Aplicação principal
│   ├── models.py           # Modelos SQLAlchemy
│   ├── routes/             # Endpoints da API
│   ├── utils/              # Utilitários (security, validators, etc.)
│   ├── extensions.py       # Configurações Flask
│   └── requirements.txt    # Dependências Python
├── frontend/               # Aplicação React
│   ├── src/
│   │   ├── components/     # Componentes React
│   │   ├── contexts/       # Contextos (Auth)
│   │   ├── routes/         # Páginas da aplicação
│   │   ├── services/       # Serviços de API
│   │   └── styles/         # CSS global
│   ├── vite.config.js      # Configuração Vite
│   └── package.json        # Dependências Node.js
├── .env                    # Configurações globais
└── README.md              # Este arquivo
```

## 🎯 Funcionalidades

### Para Usuários
- ✅ **Registro/Login** com validação
- ✅ **Feed de Posts** com paginação
- ✅ **Criar Posts** com texto e imagens
- ✅ **Editar/Excluir** posts próprios
- ✅ **Sistema de Likes** em posts
- ✅ **Comentários** em posts
- ✅ **Sistema de Seguidores**
- ✅ **Busca** de usuários
- ✅ **Perfil** personalizável

### Para Administradores
- ✅ **Painel Dashboard** com estatísticas
- ✅ **Gerenciamento de Usuários**
- ✅ **Revisão de Denúncias**
- ✅ **Logs de Segurança**
- ✅ **Configurações do Sistema**

## 🚨 Segurança - Yuri, pode tentar hackear! 🕵️‍♂️

Este projeto foi desenvolvido com foco em segurança cibernética. Yuri pode tentar:

### Ataques para Testar:
- **SQL Injection** - Protegido por SQLAlchemy ORM
- **XSS** - Protegido por sanitização de entrada
- **CSRF** - Protegido por Double Submit Cookie
- **Brute Force** - Protegido por rate limiting e lockout
- **Session Hijacking** - Protegido por fingerprinting
- **Directory Traversal** - Protegido por validações
- **API Abuse** - Protegido por rate limiting global

### Honeypots Disponíveis:
- `/admin`, `/dashboard`, `/cms`, `/painel`, `/wp-admin`

### Logs para Monitorar:
```bash
# Ver logs de segurança
tail -f backend/logs/security.log

# Ver logs de auditoria
tail -f backend/logs/audit.log
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📝 Licença

Este projeto é para fins educacionais e de pesquisa em segurança cibernética.

---

**Desenvolvido com ❤️ para demonstrar boas práticas de segurança web**

**Yuri, boa sorte na tentativa de invasão! 🔒**
