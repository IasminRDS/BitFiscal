from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Index,
    Float,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base


class Tenant(Base):
    __tablename__ = "tenants"
    __table_args__ = (Index("idx_tenant_name", "name", unique=True),)
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_user_username", "username", unique=True),
        Index("idx_user_tenant", "tenant_id"),
    )
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        String(20), default="operador", nullable=False
    )  # admin, gestor, operador
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tenant = relationship("Tenant", back_populates="users")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("idx_token_user", "user_id"),
        Index("idx_token_expires", "expires_at"),
    )
    id = Column(Integer, primary_key=True)
    token = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user = relationship("User", back_populates="refresh_tokens")


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("idx_ticket_status", "status"),
        Index("idx_ticket_tenant", "tenant_id"),
        Index("idx_ticket_solicitante", "solicitante_id"),
        Index("idx_ticket_responsavel", "responsavel_id"),
        Index("idx_ticket_criado", "criado_em"),
    )
    id = Column(Integer, primary_key=True)
    titulo = Column(String(150), nullable=False)
    descricao = Column(Text, nullable=False)
    status = Column(
        String(20), default="aberto", nullable=False
    )  # aberto, andamento, pendente_aprovacao, fechado
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    responsavel_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    solicitante_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    responsavel = relationship("User", foreign_keys=[responsavel_id])
    solicitante = relationship("User", foreign_keys=[solicitante_id])
    comentarios = relationship(
        "TicketComment", back_populates="ticket", cascade="all, delete-orphan"
    )
    anexos = relationship(
        "TicketAttachment", back_populates="ticket", cascade="all, delete-orphan"
    )


class TicketComment(Base):
    __tablename__ = "ticket_comments"
    __table_args__ = (
        Index("idx_comment_ticket", "ticket_id"),
        Index("idx_comment_autor", "autor_id"),
        Index("idx_comment_criado", "criado_em"),
    )
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    autor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    texto = Column(Text, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    ticket = relationship("Ticket", back_populates="comentarios")
    autor = relationship("User")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"
    __table_args__ = (
        Index("idx_attachment_ticket", "ticket_id"),
        Index("idx_attachment_uploader", "uploaded_by_id"),
        Index("idx_attachment_created", "created_at"),
    )
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    file_size = Column(Integer, default=0)
    ticket = relationship("Ticket", back_populates="anexos")
    uploader = relationship("User")


class BackupJob(Base):
    __tablename__ = "backup_jobs"
    __table_args__ = (
        Index("idx_backup_status", "status"),
        Index("idx_backup_iniciado", "iniciado_em"),
    )
    id = Column(Integer, primary_key=True)
    alvo = Column(String(100), nullable=False)
    status = Column(String(20), default="ok", nullable=False)  # ok, falha, pendente
    detalhe = Column(String(500), nullable=True)
    iniciado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    finalizado_em = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    duration_seconds = Column(Integer, default=0)


class UsageRule(Base):
    __tablename__ = "usage_rules"
    __table_args__ = (
        Index("idx_rule_grupo", "grupo"),
        Index("idx_rule_categoria", "categoria"),
    )
    id = Column(Integer, primary_key=True)
    grupo = Column(String(50), nullable=False)
    categoria = Column(String(50), nullable=False)
    permitido = Column(Boolean, default=False, nullable=False)
    horario = Column(String(20), default="08:00-18:00", nullable=False)


class MonitorHost(Base):
    __tablename__ = "monitor_hosts"
    __table_args__ = (
        Index("idx_host_ip", "ip", unique=True),
        Index("idx_host_status", "status"),
        Index("idx_host_atualizado", "atualizado_em"),
    )
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    ip = Column(String(15), unique=True, nullable=False)
    status = Column(
        String(20), default="desconhecido", nullable=False
    )  # online, offline, desconhecido
    ultimo_ping_ms = Column(Integer, default=0, nullable=False)
    atualizado_em = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    falhas_consecutivas = Column(Integer, default=0)
