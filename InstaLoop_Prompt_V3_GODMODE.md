# 🔱 InstaLoop — GODMODE SECURITY EDITION (Prompt V3)

Crie um projeto completo de **Mini Rede Social** chamado **InstaLoop** com backend em **Python + Flask** e frontend em **React + Vite**.
Este projeto deve ser construído como se fosse implantado em produção real e submetido a um pentest profissional. Cada camada deve ser independentemente segura — se uma camada falhar, as outras ainda protegem o sistema.

---

# 1️⃣ Backend (Flask + Blueprints + PostgreSQL)

## Estrutura de pastas:

```
backend/
├─ app.py
├─ config.py
├─ models.py
├─ extensions.py
├─ utils/
│   ├─ security.py          # Argon2id, timing-safe compare, CSRF, sanitização
│   ├─ validators.py        # Whitelist de campos, tipos, tamanhos
│   ├─ honeypot.py          # Registro silencioso de intrusões
│   ├─ audit.py             # Log estruturado JSON de todas as ações sensíveis
│   ├─ fingerprint.py       # Fingerprint multi-sinal de device/browser
│   ├─ behavioral.py        # Detecção de bots e scripts automatizados
│   └─ image_processor.py   # Re-renderização de imagens do zero
├─ routes/
│   ├─ auth.py
│   ├─ posts.py
│   ├─ users.py
│   ├─ messages.py
│   ├─ moderation.py
│   └─ admin.py             # Rota 100% via env var, nunca hardcoded
└─ static/uploads/
```

---

## 🔐 CAMADA 1 — Autenticação Blindada

### Senhas
- Hash com **Argon2id** (não bcrypt):
  - `time_cost=3`, `memory_cost=65536`, `parallelism=2`
  - Parâmetros configuráveis via `.env`
- **Timing-safe comparison** em toda verificação de senha e token:
  ```python
  import hmac
  hmac.compare_digest(hash_esperado, hash_recebido)
  ```
- Nunca retornar se o erro foi "email não encontrado" ou "senha errada" — sempre: `{"error": "Credenciais inválidas"}`

### JWT
- Algoritmo **fixado em HS256** — rejeitar qualquer token com `alg: none`, `alg: RS256` ou qualquer outro valor
- Access token: **15 minutos** de validade
- Refresh token: **7 dias**, armazenado com hash no banco, revogável individualmente
- Logout invalida o refresh token no banco (não é stateless, é intencional)
- **Session fixation protection**: gerar par de tokens completamente novos após cada login
- Refresh token entregue em **cookie HttpOnly + Secure + SameSite=Strict** (nunca no body)
- Access token armazenado **apenas em memória** no frontend (nunca localStorage/sessionStorage)

### 2FA obrigatório para admin
- TOTP (RFC 6238) com **pyotp**
- Secret gerado no cadastro do admin, armazenado encriptado no banco
- Login admin: senha → 2FA → JWT (três fatores independentes)
- Falha no 2FA: logar como tentativa suspeita, retornar mensagem genérica

### Recuperação de senha
- Token de reset: `secrets.token_urlsafe(32)` — **salvar apenas o hash SHA-256 no banco**
- Expiração: **15 minutos**
- Uso único: marcar como `usado=True` imediatamente após validação
- Rate limit: 3 tentativas por email por hora
- Email de reset nunca confirma se o email existe ou não: sempre `{"message": "Se o email existir, você receberá as instruções."}`

---

## 🔐 CAMADA 2 — Rate Limiting e Anti-Brute Force

### Fingerprint multi-sinal (não confiar só no IP)
```python
# utils/fingerprint.py
def gerar_fingerprint(request):
    dados = {
        "user_agent":       request.headers.get("User-Agent", ""),
        "accept_language":  request.headers.get("Accept-Language", ""),
        "accept_encoding":  request.headers.get("Accept-Encoding", ""),
        "accept":           request.headers.get("Accept", ""),
        "sec_ch_ua":        request.headers.get("Sec-CH-UA", ""),
        "sec_ch_platform":  request.headers.get("Sec-CH-Platform", ""),
        "sec_fetch_site":   request.headers.get("Sec-Fetch-Site", ""),
        "ip_subnet":        get_ip(request).rsplit(".", 1)[0],  # /24
    }
    return hashlib.sha256(json.dumps(dados, sort_keys=True).encode()).hexdigest()
```

### Limites por endpoint (IP + fingerprint combinados)
| Endpoint | Limite | Janela | Lockout |
|---|---|---|---|
| `/login` | 5 tentativas | 15 min | Progressivo: 15min → 1h → 24h |
| `/register` | 3 cadastros | 1h | Bloquear IP/subnet |
| `/recuperacao` | 3 tentativas | 1h | Silencioso |
| `/posts` | 20 criações | 1h | Soft block 30min |
| `/messages` | 60 mensagens | 1h | Soft block 30min |
| `/comments` | 30 comentários | 1h | Soft block 30min |
| `/api/*` (genérico) | 300 requests | 1min | Hard block 1h |

### Lockout progressivo e silencioso
- Após lockout: **sempre retornar HTTP 200** com mensagem genérica
- Nunca revelar que o usuário está bloqueado, por quanto tempo, ou por quê
- Logar cada tentativa durante lockout como `lockout_probe`

### Behavioral analysis (detecção de bots)
```python
# utils/behavioral.py
def detectar_comportamento_automatizado(user_id, acao):
    # Humanos não fazem 10 ações iguais em 5 segundos
    acoes = AuditLog.query.filter(
        AuditLog.user_id == user_id,
        AuditLog.acao == acao,
        AuditLog.timestamp > datetime.utcnow() - timedelta(seconds=5)
    ).count()
    if acoes >= 10:
        banir_temporariamente(user_id, minutos=60)
        alertar_admin(user_id, "bot_detected", acao)
        return True

    # Detectar padrão de enumeração de UUIDs
    uuids_tentados = AuditLog.query.filter(
        AuditLog.user_id == user_id,
        AuditLog.resultado == "not_found",
        AuditLog.timestamp > datetime.utcnow() - timedelta(minutes=5)
    ).count()
    if uuids_tentados >= 20:
        banir_temporariamente(user_id, minutos=120)
        return True

    return False
```

---

## 🔐 CAMADA 3 — Honeypots e Deception

### Rotas honeypot no backend (retornam HTTP 200 com JSON falso)
Registrar silenciosamente **IP, User-Agent, headers completos, body, timestamp, rota** em `HoneypotLogs`:
```
/admin
/dashboard
/cms
/painel
/wp-admin
/wp-login.php
/administrator
/login-admin
/api/admin
/api/v1/admin
/api/v2/admin
/phpmyadmin
/config
/config.php
/.env
/.git
/backup
/db
/database
/setup
/install
/shell
/cmd
/exec
/eval
/api/users (sem auth — retornar lista falsa)
/api/debug
/api/test
/swagger
/api-docs
/graphql
```

### JSON falso para confundir
```python
RESPOSTAS_HONEYPOT = [
    {"status": "ok", "data": []},
    {"success": True, "token": "eyJ...falso..."},
    {"users": [], "total": 0, "page": 1},
    {"message": "Carregando...", "progress": 23},
]
# Retornar aleatoriamente para dificultar pattern matching
```

### Rota admin real
- **100% via variável de ambiente** `ADMIN_ROUTE_SECRET`
- Nunca escrita em código, logs ou respostas
- Protegida por: rota secreta + JWT válido + role admin + 2FA verificado + IP allowlist opcional

---

## 🔐 CAMADA 4 — Validação, Sanitização e IDOR

### IDOR Protection
- Todos os IDs públicos como **UUID v4** (nunca inteiros sequenciais)
- **Ownership check obrigatório** em TODOS os endpoints de modificação:
  ```python
  def verificar_dono(user_id, recurso_id, model):
      recurso = model.query.get(recurso_id)
      if not recurso or recurso.user_id != user_id:
          # Não revelar se o recurso existe
          abort(404)
  ```
- Respostas de recursos não autorizados: sempre 404 (nunca 403 — 403 confirma existência)

### Mass Assignment Protection
- Whitelist explícita de campos em cada endpoint — nunca `**request.json`:
  ```python
  CAMPOS_PERMITIDOS_PERFIL = {"bio", "avatar_url", "is_private"}
  dados = {k: v for k, v in request.json.items() if k in CAMPOS_PERMITIDOS_PERFIL}
  ```
- Campos como `is_admin`, `is_banned`, `password_hash` nunca aceitáveis via API pública

### Parameter Pollution
- Rejeitar requests com chaves duplicadas no JSON
- Rejeitar query strings duplicadas (`?id=1&id=2`)

### Sanitização de inputs
- **bleach** em todos os campos de texto antes de salvar
- Rejeitar e logar qualquer input com: `<script`, `javascript:`, `onerror=`, `onload=`, `eval(`, `document.cookie`, `fetch(`, `XMLHttpRequest`, `--`, `/*`, `DROP`, `UNION SELECT`, `../`, `..\`
- **Proteção contra ReDoS**: não usar regex com backtracking em inputs de usuário; usar validações simples com limite de tamanho antes da regex

### SQL Injection
- **Exclusivamente ORM (SQLAlchemy)** — zero queries raw com f-string ou concatenação
- Proibido em qualquer arquivo: `db.engine.execute(f"...")`

### XSS
- CSP header bloqueando scripts inline
- DOMPurify no frontend antes de renderizar qualquer conteúdo de usuário
- Outputs sempre escapados pelo template engine

---

## 🔐 CAMADA 5 — Upload de Arquivos (Zero Trust)

```python
# utils/image_processor.py
import magic
from PIL import Image
import io, uuid

MIME_PERMITIDOS = {'image/jpeg', 'image/png', 'image/webp'}
TAMANHO_MAX = 5 * 1024 * 1024  # 5MB

def processar_imagem_segura(file_bytes):
    # 1. Checar tamanho
    if len(file_bytes) > TAMANHO_MAX:
        raise ValueError("Arquivo muito grande")

    # 2. Validar magic bytes reais (não Content-Type)
    mime = magic.from_buffer(file_bytes[:2048], mime=True)
    if mime not in MIME_PERMITIDOS:
        raise ValueError("Tipo não permitido")

    # 3. Re-renderizar do zero (destrói qualquer payload escondido, metadados, EXIF)
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()  # detecta corrupção

        img = Image.open(io.BytesIO(file_bytes))  # reabrir após verify()
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')

        output = io.BytesIO()
        formato = 'JPEG' if mime == 'image/jpeg' else mime.split('/')[1].upper()
        img.save(output, format=formato, optimize=True,
                 exif=b"",           # remover EXIF
                 icc_profile=None)   # remover ICC profile

        # 4. Nome UUID — nunca usar nome original
        extensao = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp'}[mime]
        nome_final = f"{uuid.uuid4()}{extensao}"

        return output.getvalue(), nome_final

    except Exception:
        raise ValueError("Arquivo inválido")
```

- Servir uploads com `Content-Disposition: attachment` — nunca executável
- Uploads em diretório sem permissão de execução no servidor
- Nunca servir com Content-Type dinâmico baseado no nome do arquivo

---

## 🔐 CAMADA 6 — Headers de Segurança (todas as respostas)

```python
@app.after_request
def aplicar_headers_seguranca(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'

    # Remover headers que revelam a stack
    response.headers.pop('Server', None)
    response.headers.pop('X-Powered-By', None)
    response.headers.pop('X-Flask-Version', None)

    # Cache zero em endpoints autenticados
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        response.headers['Pragma'] = 'no-cache'

    return response
```

---

## 🔐 CAMADA 7 — Proteção contra SSRF e Path Traversal

```python
# SSRF — bloquear IPs privados se aceitar URLs
import ipaddress

REDES_PRIVADAS = [
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('169.254.0.0/16'),   # link-local
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
]

def validar_url_externa(url):
    from urllib.parse import urlparse
    import socket
    hostname = urlparse(url).hostname
    ip = ipaddress.ip_address(socket.gethostbyname(hostname))
    for rede in REDES_PRIVADAS:
        if ip in rede:
            raise ValueError("URL não permitida")

# Path Traversal — uploads nunca usam nome original
# (coberto na CAMADA 5 com UUID)

# Bloquear acesso a arquivos sensíveis
ARQUIVOS_SENSIVEIS = ['.env', '.git', 'config.py', 'requirements.txt',
                      'docker-compose.yml', 'Dockerfile', '.htaccess',
                      'web.config', 'settings.py', '__pycache__']

@app.before_request
def bloquear_sensiveis():
    for arq in ARQUIVOS_SENSIVEIS:
        if arq.lower() in request.path.lower():
            honeypot_log(request, "sensitive_file_probe")
            return jsonify({"error": "Not found"}), 404
```

---

## 🔐 CAMADA 8 — CSRF

- Token CSRF em **cookie SameSite=Strict + HttpOnly**
- Validar token no header `X-CSRF-Token` em todos os endpoints POST/PUT/PATCH/DELETE
- Double Submit Cookie pattern
- Origin/Referer validation como camada adicional

---

## 🔐 CAMADA 9 — Logging e Auditoria

### Log estruturado (JSON) obrigatório para:
- Login (sucesso/falha + motivo genérico interno)
- Registro de usuários
- Alterações de perfil, senha, email
- Criação/edição/exclusão de posts
- Follows, bloqueios, denúncias
- Mensagens enviadas/apagadas
- Tokens JWT inválidos/expirados/manipulados
- Acessos a rotas honeypot (com payload completo)
- Tentativas durante lockout
- Upload de arquivos (aceitos e rejeitados)
- Detecção de comportamento automatizado

### Campos obrigatórios em cada log:
```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "WARNING",
  "event": "login_failed",
  "ip": "1.2.3.4",
  "ip_subnet": "1.2.3",
  "fingerprint": "sha256...",
  "user_agent": "Mozilla/5.0...",
  "user_id": null,
  "endpoint": "/api/auth/login",
  "method": "POST",
  "resultado": "invalid_credentials",
  "detalhes": {}
}
```

### Nunca logar:
- Senhas (nem parcialmente)
- Tokens completos (apenas primeiros 8 chars para referência)
- Dados de cartão ou pagamento
- Conteúdo de mensagens privadas

---

# 2️⃣ Frontend (React + Vite)

## Estrutura de pastas:

```
frontend/
├─ vite.config.js
├─ src/
│   ├─ main.jsx
│   ├─ App.jsx
│   ├─ routes/
│   │   ├─ Home.jsx
│   │   ├─ Login.jsx
│   │   ├─ Register.jsx
│   │   ├─ Profile.jsx
│   │   ├─ Feed.jsx
│   │   ├─ Messages.jsx
│   │   ├─ HoneypotPage.jsx
│   │   └─ AdminPage.jsx        # Lazy, chunk separado, só após auth
│   ├─ components/
│   └─ services/
│       ├─ authService.js       # Tokens em memória, nunca storage
│       ├─ postService.js
│       ├─ userService.js
│       └─ messageService.js
└─ assets/
```

---

## 🔐 CAMADA 10 — DevTools Invisibility

### vite.config.js — build blindado:
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: false,               // ZERO source maps
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,         // remove todos os console.*
        drop_debugger: true,        // remove debugger statements
        passes: 3,                  // 3 passagens de otimização
        pure_funcs: ['console.log', 'console.warn', 'console.error',
                     'console.info', 'console.debug', 'console.trace'],
      },
      mangle: {
        toplevel: true,             // renomear variáveis do topo
        eval: true,
        properties: {
          regex: /^_/,              // ofuscar propriedades com _
        },
      },
      format: {
        comments: false,            // zero comentários no bundle
      },
    },
    rollupOptions: {
      output: {
        // Nomes de chunks com hash — impossível deduzir conteúdo
        chunkFileNames: 'assets/[hash].js',
        entryFileNames: 'assets/[hash].js',
        assetFileNames: 'assets/[hash].[ext]',
        manualChunks: {
          // vendor em chunk separado
          vendor: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
})
```

### Console bloqueado em produção:
```js
// main.jsx — executar antes de qualquer coisa
if (import.meta.env.PROD) {
  const noop = () => {};
  Object.keys(console).forEach(key => {
    try { console[key] = noop; } catch(e) {}
  });
  // Também bloquear reassignment
  Object.freeze(console);
}
```

### Detecção de DevTools aberto:
```js
// utils/devtools-detector.js
let devtoolsAberto = false;

const detectar = () => {
  const threshold = 200;
  const aberto =
    window.outerWidth - window.innerWidth > threshold ||
    window.outerHeight - window.innerHeight > threshold;

  if (aberto && !devtoolsAberto) {
    devtoolsAberto = true;
    // Reportar silenciosamente ao backend
    fetch('/api/telemetry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: 'devtools_opened',
        ts: Date.now(),
        url: window.location.pathname,
      }),
      keepalive: true,
    }).catch(() => {});
  } else if (!aberto) {
    devtoolsAberto = false;
  }
};

setInterval(detectar, 1000);
window.addEventListener('resize', detectar);
```

### Rota admin — invisível até autenticação:
```jsx
// App.jsx — admin NUNCA no bundle principal
const AdminPage = React.lazy(() =>
  import(/* webpackChunkName: "[hash]" */ './routes/AdminPage')
);

// A rota admin não aparece no código — lida via env:
const ADMIN_PATH = import.meta.env.VITE_ADMIN_ROUTE; // ex: "/x7k2m9p4"

// Nunca listar ADMIN_PATH em nenhum lugar visível
// O chunk só é baixado quando o usuário navega para a rota E está autenticado como admin
```

### Tokens JWT em memória (nunca storage):
```js
// services/authService.js
let accessToken = null; // memória pura, some ao fechar a aba

export const setToken = (token) => { accessToken = token; };
export const getToken = () => accessToken;
export const clearToken = () => { accessToken = null; };

// Refresh token: vem em cookie HttpOnly do backend (inacessível via JS)
// Renovação automática: interceptor no axios detecta 401 e chama /refresh
```

---

## 🔐 CAMADA 11 — Honeypots no Frontend

### Rotas honeypot no React Router:
```jsx
// Todas redirecionam para HoneypotPage silenciosamente
const rotasHoneypot = [
  '/admin', '/dashboard', '/cms', '/painel',
  '/wp-admin', '/administrator', '/login-admin',
  '/api', '/config', '/setup', '/install',
];

// HoneypotPage: reporta ao backend e exibe loading infinito
```

```jsx
// HoneypotPage.jsx
import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

export default function HoneypotPage() {
  const location = useLocation();

  useEffect(() => {
    fetch('/api/telemetry', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        event: 'honeypot_route_accessed',
        route: location.pathname,
        ts: Date.now(),
        referrer: document.referrer,
      }),
      keepalive: true,
    }).catch(() => {});
  }, []);

  // Loading infinito — nunca resolve
  return (
    <div style={{ display: 'flex', justifyContent: 'center',
                  alignItems: 'center', height: '100vh' }}>
      <div className="spinner" />
      <p>Carregando...</p>
    </div>
  );
}
```

---

## 🔐 CAMADA 12 — Segurança de Renderização

- **DOMPurify** em todo conteúdo de usuário antes de renderizar:
  ```jsx
  import DOMPurify from 'dompurify';
  <p dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(post.content) }} />
  ```
- **Nunca usar `eval()`**, `innerHTML` sem sanitização, ou `dangerouslySetInnerHTML` sem DOMPurify
- **Zero validação de segurança no frontend** — apenas UX (ex: "campo obrigatório")
- Toda validação real: exclusivamente no backend
- Nunca exibir mensagens de erro do backend — sempre mensagens amigáveis genéricas

---

# 3️⃣ Banco de Dados (PostgreSQL)

```sql
-- UUIDs em todos os IDs públicos
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(30) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    bio TEXT,
    avatar_url TEXT,
    is_private BOOLEAN DEFAULT FALSE,
    is_admin BOOLEAN DEFAULT FALSE,
    is_banned BOOLEAN DEFAULT FALSE,
    totp_secret TEXT,                    -- 2FA admin
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT,
    media_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(post_id, user_id)
);

CREATE TABLE follows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(10) NOT NULL CHECK (status IN ('pending', 'accepted')),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(follower_id, following_id)
);

CREATE TABLE blocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    blocker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(blocker_id, blocked_id)
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT,
    media_url TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,     -- nunca o token raw
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE password_resets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,     -- SHA-256 do token
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(10) NOT NULL CHECK (target_type IN ('post', 'user')),
    target_id UUID NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(10) DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE honeypot_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ip TEXT NOT NULL,
    ip_subnet TEXT,
    fingerprint TEXT,
    user_agent TEXT,
    headers_json JSONB,
    route TEXT NOT NULL,
    method TEXT,
    payload_preview TEXT,
    event_type TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id UUID,
    ip TEXT,
    fingerprint TEXT,
    user_agent TEXT,
    resultado TEXT,
    details_json JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_receiver ON messages(receiver_id);
CREATE INDEX idx_honeypot_ip ON honeypot_logs(ip);
CREATE INDEX idx_honeypot_timestamp ON honeypot_logs(timestamp);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
```

---

# 4️⃣ Funcionalidades obrigatórias

1. Cadastro/login/recuperação de senha (token único, expiração 15min, hash no banco)
2. 2FA TOTP obrigatório para admin
3. Perfil público/privado, edição de foto/bio/privacidade
4. Bloqueio de usuários (invisibilidade total: feed, busca, API)
5. CRUD de posts com texto e imagens (imagens re-renderizadas)
6. Curtidas e comentários com ownership check
7. Feed cronológico reverso respeitando bloqueios
8. Follow/unfollow com aprovação para perfis privados
9. Mensagens diretas + fotos + apagar (indicador "mensagem apagada")
10. Denúncias de posts e perfis
11. Painel admin seguro com métricas (usuários, posts, denúncias pendentes)
12. Honeypots frontend + backend (loading infinito / JSON falso)
13. DevTools bloqueados: sem source maps, console zerado, chunks com hash
14. Detecção e log de DevTools aberto
15. Detecção e log de comportamento automatizado (bots)
16. Rate limiting por IP + fingerprint multi-sinal
17. Lockout progressivo silencioso
18. Tokens JWT em memória no frontend
19. Refresh token em cookie HttpOnly
20. Headers de segurança em todas as respostas
21. UUIDs em todos os IDs públicos
22. Logging e auditoria JSON estruturado

---

# 5️⃣ Proteções implementadas (checklist completo)

| Ataque | Proteção |
|---|---|
| Brute Force | Rate limit + lockout progressivo silencioso |
| Flood / DDoS app | Rate limit por IP + fingerprint + behavioral |
| SQL Injection | ORM exclusivo, zero raw queries |
| XSS | CSP + bleach + DOMPurify + sanitização |
| CSRF | Token double-submit + SameSite=Strict |
| IDOR | UUIDs + ownership check obrigatório |
| JWT Algorithm Confusion | alg fixado, rejeitar none/RS256 |
| Timing Attack | hmac.compare_digest em todas as comparações |
| Session Fixation | Novo token após cada login |
| Path Traversal | UUID nos uploads, nunca nome original |
| SSRF | Blocklist de IPs privados |
| Mass Assignment | Whitelist explícita de campos |
| Parameter Pollution | Rejeitar chaves duplicadas |
| ReDoS | Sem regex complexo em inputs, limite de tamanho |
| Clickjacking | X-Frame-Options DENY + CSP frame-ancestors |
| Upload malicioso | magic bytes + re-renderização do zero |
| Account Takeover | Token reset com hash + uso único + 15min |
| Admin Enumeration | Rota via env, honeypots em rotas óbvias |
| Stack Disclosure | Headers removidos, erros genéricos |
| Sensitive File Access | Blocklist + honeypot log |
| Bot / Script | Behavioral analysis + ban automático |
| DevTools Inspection | Sem source maps, console zerado, chunks hash |
| 2FA Bypass | TOTP obrigatório + mensagem genérica em falha |

---

# 6️⃣ .env obrigatório

```env
# Banco
DATABASE_URL=postgresql://user:pass@localhost:5432/instaloop

# JWT
JWT_SECRET_KEY=<256-bit random — use: python -c "import secrets; print(secrets.token_hex(32))">
JWT_ACCESS_TOKEN_EXPIRES=900        # 15 minutos
JWT_REFRESH_TOKEN_EXPIRES=604800    # 7 dias

# Admin
ADMIN_ROUTE_SECRET=<slug aleatório ex: x7k2m9p4>

# Argon2
ARGON2_TIME_COST=3
ARGON2_MEMORY_COST=65536
ARGON2_PARALLELISM=2

# Uploads
UPLOAD_MAX_SIZE_MB=5
UPLOAD_DIR=static/uploads

# Frontend
VITE_ADMIN_ROUTE=<mesmo slug do ADMIN_ROUTE_SECRET>
VITE_API_URL=http://localhost:5000

# Alertas (opcional)
HONEYPOT_WEBHOOK_URL=<webhook discord/slack para alertas em tempo real>
```

---

# 7️⃣ Design (Frontend)

- Inspiração visual: Instagram + Twitter modernos
- **Dark mode** como padrão, toggle para light mode
- Tipografia: fonte display marcante para logo + fonte sans-serif limpa para corpo
- Paleta: tons escuros com 1 cor de acento vibrante (não roxo genérico)
- SVGs inline em todos os ícones (nunca icon fonts ou emojis de teclado)
- Skeleton loading em feeds, perfis e mensagens
- Micro-animações em curtidas, follows, envio de mensagens
- Layout responsivo (mobile-first)
- Feedback visual em todas as ações (loading spinner, toast de sucesso/erro)
- Componentes reutilizáveis: Post, Comment, Avatar, Button, Modal, NavBar, Skeleton

---

> 🏆 **Meta**: quando o YuriRDev abrir o DevTools, não ver nada útil.
> Quando tentar `/admin`, cair num honeypot silencioso.
> Quando tentar brute force, ser banido sem saber.
> Quando tentar injetar SQL/XSS, ter o payload logado com IP e fingerprint.
> Quando tentar IDOR, receber 404 como se o recurso não existisse.
> **O sistema não grita que foi atacado. Ele observa, registra e protege em silêncio.**
