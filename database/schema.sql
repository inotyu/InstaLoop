-- InstaLoop Database Schema
-- PostgreSQL com UUIDs e índices otimizados para segurança

-- Extensão UUID para geração de IDs seguros
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Função para trigger de updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Tabela de usuários com campos de segurança
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
    totp_secret TEXT,                    -- 2FA para admins
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Trigger para updated_at
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Índices para performance e segurança
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_banned ON users(is_banned);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_locked_until ON users(locked_until) WHERE locked_until IS NOT NULL;

-- Tabela de posts com validações
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT,
    media_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints de segurança
    CONSTRAINT posts_content_or_media CHECK (
        (content IS NOT NULL AND content != '') OR 
        (media_url IS NOT NULL AND media_url != '')
    )
);

-- Trigger para updated_at
CREATE TRIGGER update_posts_updated_at 
    BEFORE UPDATE ON posts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Índices
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_created_at ON posts(created_at DESC);
CREATE INDEX idx_posts_user_created ON posts(user_id, created_at DESC);

-- Tabela de comentários
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraint de segurança
    CONSTRAINT comments_content_not_empty CHECK (content IS NOT NULL AND content != '')
);

-- Índices
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_comments_created_at ON comments(created_at DESC);

-- Tabela de likes com restrição única
CREATE TABLE likes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Impedir likes duplicados
    UNIQUE(post_id, user_id)
);

-- Índices
CREATE INDEX idx_likes_post_id ON likes(post_id);
CREATE INDEX idx_likes_user_id ON likes(user_id);
CREATE INDEX idx_likes_created_at ON likes(created_at DESC);

-- Tabela de follows com status
CREATE TABLE follows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(10) NOT NULL CHECK (status IN ('pending', 'accepted')),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Impedir follow duplicado e self-follow
    UNIQUE(follower_id, following_id),
    CONSTRAINT no_self_follow CHECK (follower_id != following_id)
);

-- Índices
CREATE INDEX idx_follows_follower_id ON follows(follower_id);
CREATE INDEX idx_follows_following_id ON follows(following_id);
CREATE INDEX idx_follows_status ON follows(status);
CREATE INDEX idx_follows_created_at ON follows(created_at DESC);

-- Tabela de blocks
CREATE TABLE blocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    blocker_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Impedir block duplicado e self-block
    UNIQUE(blocker_id, blocked_id),
    CONSTRAINT no_self_block CHECK (blocker_id != blocked_id)
);

-- Índices
CREATE INDEX idx_blocks_blocker_id ON blocks(blocker_id);
CREATE INDEX idx_blocks_blocked_id ON blocks(blocked_id);
CREATE INDEX idx_blocks_created_at ON blocks(created_at DESC);

-- Tabela de mensagens com soft delete
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT,
    media_url TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraint de segurança
    CONSTRAINT messages_content_or_media CHECK (
        (content IS NOT NULL AND content != '') OR 
        (media_url IS NOT NULL AND media_url != '')
    )
);

-- Índices
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_receiver_id ON messages(receiver_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX idx_messages_is_deleted ON messages(is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX idx_messages_conversation ON messages(
    LEAST(sender_id, receiver_id), 
    GREATEST(sender_id, receiver_id), 
    created_at DESC
) WHERE is_deleted = FALSE;

-- Tabela de refresh tokens (segurança JWT)
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,     -- SHA-256 do token, nunca o token raw
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_refresh_tokens_revoked ON refresh_tokens(revoked) WHERE revoked = FALSE;

-- Tabela de password resets
CREATE TABLE password_resets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,     -- SHA-256 do token
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_password_resets_user_id ON password_resets(user_id);
CREATE INDEX idx_password_resets_hash ON password_resets(token_hash);
CREATE INDEX idx_password_resets_expires_at ON password_resets(expires_at);
CREATE INDEX idx_password_resets_used ON password_resets(used) WHERE used = FALSE;

-- Tabela de denúncias
CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(10) NOT NULL CHECK (target_type IN ('post', 'user')),
    target_id UUID NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(10) DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed')),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraint de segurança
    CONSTRAINT reports_reason_not_empty CHECK (reason IS NOT NULL AND reason != '')
);

-- Índices
CREATE INDEX idx_reports_reporter_id ON reports(reporter_id);
CREATE INDEX idx_reports_target ON reports(target_type, target_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);

-- Tabela de logs de honeypot (segurança)
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

-- Índices para performance de logs
CREATE INDEX idx_honeypot_ip ON honeypot_logs(ip);
CREATE INDEX idx_honeypot_ip_subnet ON honeypot_logs(ip_subnet);
CREATE INDEX idx_honeypot_fingerprint ON honeypot_logs(fingerprint);
CREATE INDEX idx_honeypot_timestamp ON honeypot_logs(timestamp DESC);
CREATE INDEX idx_honeypot_route ON honeypot_logs(route);
CREATE INDEX idx_honeypot_event_type ON honeypot_logs(event_type);

-- Tabela de auditoria (logs estruturados)
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

-- Índices para performance de auditoria
CREATE INDEX idx_audit_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_resultado ON audit_logs(resultado);
CREATE INDEX idx_audit_target ON audit_logs(target_type, target_id);
CREATE INDEX idx_audit_ip ON audit_logs(ip);

-- Particionamento para logs grandes (opcional, para alta escala)
-- CREATE TABLE audit_logs_y2024m01 PARTITION OF audit_logs
-- FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Views para consultas comuns
CREATE VIEW user_stats AS
SELECT 
    u.id,
    u.username,
    u.created_at,
    COUNT(DISTINCT p.id) as posts_count,
    COUNT(DISTINCT CASE WHEN f.status = 'accepted' THEN f.id END) as followers_count,
    COUNT(DISTINCT CASE WHEN f2.status = 'accepted' THEN f2.id END) as following_count,
    COUNT(DISTINCT CASE WHEN l.id IS NOT NULL THEN l.id END) as likes_given,
    COUNT(DISTINCT CASE WHEN l2.id IS NOT NULL THEN l2.id END) as likes_received
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
LEFT JOIN follows f ON u.id = f.following_id AND f.status = 'accepted'
LEFT JOIN follows f2 ON u.id = f.follower_id AND f2.status = 'accepted'
LEFT JOIN likes l ON u.id = l.user_id
LEFT JOIN likes l2 ON u.id = l2.user_id AND l2.post_id = p.id
GROUP BY u.id, u.username, u.created_at;

-- View para posts com informações do autor
CREATE VIEW posts_with_author AS
SELECT 
    p.id,
    p.content,
    p.media_url,
    p.created_at,
    p.updated_at,
    u.id as author_id,
    u.username as author_username,
    u.avatar_url as author_avatar,
    u.is_private as author_is_private,
    COUNT(DISTINCT l.id) as likes_count,
    COUNT(DISTINCT c.id) as comments_count
FROM posts p
JOIN users u ON p.user_id = u.id
LEFT JOIN likes l ON p.id = l.post_id
LEFT JOIN comments c ON p.id = c.post_id
GROUP BY p.id, p.content, p.media_url, p.created_at, p.updated_at, 
         u.id, u.username, u.avatar_url, u.is_private;

-- Função para limpeza automática de dados expirados
CREATE OR REPLACE FUNCTION cleanup_expired_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- Limpar refresh tokens expirados
    DELETE FROM refresh_tokens WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Limpar password resets expirados
    DELETE FROM password_resets WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- Limpar honeypot logs antigos (manter apenas 30 dias)
    DELETE FROM honeypot_logs WHERE timestamp < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    -- Limpar audit logs antigos (manter apenas 90 dias)
    DELETE FROM audit_logs WHERE timestamp < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS deleted_count = deleted_count + ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Trigger para limpeza automática (opcional)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('cleanup-expired-data', '0 2 * * *', 'SELECT cleanup_expired_data();');

-- Políticas de segurança (Row Level Security - RLS)
-- Habilitar RLS nas tabelas sensíveis
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Políticas básicas (exemplo - implementar conforme necessidade)
-- CREATE POLICY users_own_data ON users
--     FOR ALL TO authenticated_users
--     USING (id = current_setting('app.current_user_id')::uuid);

-- Funções para verificação de permissões
CREATE OR REPLACE FUNCTION can_view_user(target_user_id UUID, current_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- Usuário pode ver seu próprio perfil
    IF target_user_id = current_user_id THEN
        RETURN TRUE;
    END IF;
    
    -- Verificar se não está bloqueado
    IF EXISTS (
        SELECT 1 FROM blocks 
        WHERE (blocker_id = target_user_id AND blocked_id = current_user_id)
        OR (blocker_id = current_user_id AND blocked_id = target_user_id)
    ) THEN
        RETURN FALSE;
    END IF;
    
    -- Verificar se perfil é público ou se segue
    RETURN (
        SELECT (is_private = FALSE) OR 
               EXISTS (
                   SELECT 1 FROM follows 
                   WHERE follower_id = current_user_id 
                   AND following_id = target_user_id 
                   AND status = 'accepted'
               )
        FROM users WHERE id = target_user_id
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Estatísticas do banco para otimização
ANALYZE;

-- Comentários sobre segurança implementada:
-- 1. UUIDs em todos os IDs públicos (prevenção de enumeração)
-- 2. Índices otimizados para performance e segurança
-- 3. Constraints para integridade dos dados
-- 4. Triggers para timestamps automáticos
-- 5. Views para consultas com otimização
-- 6. Funções de limpeza automática
-- 7. Preparação para Row Level Security
-- 8. Logs estruturados para auditoria
-- 9. Hashes em vez de dados sensíveis (tokens, senhas)
-- 10. Relações com CASCADE para consistência
