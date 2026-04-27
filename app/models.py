from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from datetime import datetime
from .db import Base


class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    canal = Column(String, default="presencial")
    cliente = Column(String)
    assunto = Column(String)
    prioridade = Column(String, default="media")
    status = Column(String, default="aberto")
    criado_em = Column(DateTime, default=datetime.utcnow)


class BackupJob(Base):
    __tablename__ = "backup_jobs"
    id = Column(Integer, primary_key=True, index=True)
    alvo = Column(String)
    status = Column(String, default="ok")
    detalhe = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)


class UsageRule(Base):
    __tablename__ = "usage_rules"
    id = Column(Integer, primary_key=True, index=True)
    grupo = Column(String)  # ex: Atendimento
    categoria = Column(String)  # ex: Streaming
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
