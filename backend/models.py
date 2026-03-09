from datetime import datetime
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR

from extensions import db


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.Text)
    is_private = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    totp_secret = db.Column(db.Text)  # 2FA admin
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic', cascade='all, delete-orphan')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic', cascade='all, delete-orphan')
    refresh_tokens = db.relationship('RefreshToken', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    password_resets = db.relationship('PasswordReset', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reports_made = db.relationship('Report', foreign_keys='Report.reporter_id', backref='reporter', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    followers = db.relationship(
        'Follow',
        foreign_keys='Follow.follower_id',
        backref='following',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    following = db.relationship(
        'Follow',
        foreign_keys='Follow.following_id',
        backref='follower',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )


class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    media_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='post', lazy='dynamic', cascade='all, delete-orphan')


class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    post_id = db.Column(GUID(), db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Like(db.Model):
    __tablename__ = 'likes'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    post_id = db.Column(GUID(), db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('post_id', 'user_id'),)


class Follow(db.Model):
    __tablename__ = 'follows'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    follower_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    following_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(10), nullable=False, default='pending')  # pending, accepted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('follower_id', 'following_id'),)


class Block(db.Model):
    __tablename__ = 'blocks'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    blocker_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    blocked_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('blocker_id', 'blocked_id'),)


class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    sender_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    media_url = db.Column(db.Text)
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RefreshToken(db.Model):
    __tablename__ = 'refresh_tokens'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.Text, unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PasswordReset(db.Model):
    __tablename__ = 'password_resets'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    token_hash = db.Column(db.Text, unique=True, nullable=False)  # SHA-256 do token
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    reporter_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=False)
    target_type = db.Column(db.String(10), nullable=False)  # post, user
    target_id = db.Column(GUID(), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(10), default='pending')  # pending, reviewed, dismissed
    reviewed_at = db.Column(db.DateTime)
    reviewed_by = db.Column(GUID(), db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class HoneypotLog(db.Model):
    __tablename__ = 'honeypot_logs'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    ip = db.Column(db.Text, nullable=False)
    ip_subnet = db.Column(db.Text)
    fingerprint = db.Column(db.Text)
    user_agent = db.Column(db.Text)
    headers_json = db.Column(db.JSON)
    route = db.Column(db.Text, nullable=False)
    method = db.Column(db.Text)
    payload_preview = db.Column(db.Text)
    event_type = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.Text)
    target_id = db.Column(GUID())
    ip = db.Column(db.Text)
    fingerprint = db.Column(db.Text)
    user_agent = db.Column(db.Text)
    resultado = db.Column(db.Text)
    details_json = db.Column(db.JSON)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
