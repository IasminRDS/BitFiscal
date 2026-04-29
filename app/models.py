from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    tenant_id = Column(Integer, default=1)
    role = Column(String, default="user")


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String)
    descricao = Column(Text)
    status = Column(String, default="aberto")
    tenant_id = Column(Integer)
    solicitante_id = Column(Integer)
    responsavel_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class BackupJob(Base):
    __tablename__ = "backup_jobs"
    id = Column(Integer, primary_key=True, index=True)
    alvo = Column(String)
    status = Column(String)
    detalhe = Column(String, nullable=True)
    iniciado_em = Column(DateTime(timezone=True), server_default=func.now())
    finalizado_em = Column(DateTime(timezone=True), nullable=True)


class UsageRule(Base):
    __tablename__ = "usage_rules"
    id = Column(Integer, primary_key=True, index=True)
    grupo = Column(String)
    categoria = Column(String)
    permitido = Column(Boolean, default=False)
    horario = Column(String)


class MonitorHost(Base):
    __tablename__ = "monitor_hosts"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    ip = Column(String)
