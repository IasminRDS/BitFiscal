from pydantic import BaseModel
from datetime import datetime


class TicketCreate(BaseModel):
    canal: str
    cliente: str
    assunto: str
    prioridade: str


class BackupCreate(BaseModel):
    alvo: str
    status: str
    detalhe: str | None = None


class UsageRuleCreate(BaseModel):
    grupo: str
    categoria: str
    permitido: bool
    horario: str


class MonitorHostCreate(BaseModel):
    nome: str
    ip: str


class MonitorHostUpdate(BaseModel):
    status: str
    ultimo_ping_ms: int


class TicketOut(BaseModel):
    id: int
    canal: str
    cliente: str
    assunto: str
    prioridade: str
    status: str
    criado_em: datetime

    class Config:
        from_attributes = True
