from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base


class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    users = relationship("User", back_populates="tenant")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(String, default="operador")  # admin, gestor, operador
    created_at = Column(DateTime, default=datetime.utcnow)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    tenant = relationship("Tenant", back_populates="users")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)
    revoked = Column(Boolean, default=False)
    user = relationship("User", back_populates="refresh_tokens")


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    titulo = Column(String)
    descricao = Column(Text)
    status = Column(
        String, default="aberto"
    )  # aberto, andamento, pendente_aprovacao, fechado
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow)

    responsavel_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    solicitante_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))

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
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    autor_id = Column(Integer, ForeignKey("users.id"))
    texto = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="comentarios")
    autor = relationship("User")


class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"))
    filename = Column(String)
    path = Column(String)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", back_populates="anexos")
    uploader = relationship("User")


class BackupJob(Base):
    __tablename__ = "backup_jobs"
    id = Column(Integer, primary_key=True, index=True)
    alvo = Column(String)
    status = Column(String, default="ok")
    detalhe = Column(String, nullable=True)
    iniciado_em = Column(DateTime, default=datetime.utcnow)
    finalizado_em = Column(DateTime, default=datetime.utcnow)


class UsageRule(Base):
    __tablename__ = "usage_rules"
    id = Column(Integer, primary_key=True, index=True)
    grupo = Column(String)
    categoria = Column(String)
    permitido = Column(Boolean, default=False)
    horario = Column(String, default="08:00-18:00")


class MonitorHost(Base):
    __tablename__ = "monitor_hosts"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    ip = Column(String)
    status = Column(String, default="desconhecido")
    ultimo_ping_ms = Column(Integer, default=0)
    atualizado_em = Column(DateTime, default=datetime.utcnow)
