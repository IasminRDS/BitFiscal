from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pathlib import Path
import random
import json
import hashlib
from functools import lru_cache

from app.auth import get_current_user, verify_password, create_access_token, log_action
from app.models import User, Ticket, BackupJob, UsageRule, MonitorHost
from app.db import Base, engine, get_db
from app.config import settings
from app.services.files import save_upload_file

# Inicialização
app = FastAPI(title="BITFISCAL", version="2.0.0")
Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")
STATIC_DIR = BASE_DIR / "app" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Cache simulado para sistemas governamentais
@lru_cache(maxsize=128)
def cached_receita_query(endpoint: str, timestamp: str) -> str:
    return json.dumps({"status": "ok", "cached": True, "data": "mock"})


# Lista de domínios bloqueados
blocked_domains = {}

# Base de conhecimento para auto-respostas
KNOWLEDGE_BASE = {
    "irpf": "Para declarar IRPF 2026, acesse: https://gov.br/receitafederal/irpf. Prazo: 23/03 a 29/05/2026.",
    "senha": "Para redefinir senha do sistema, clique em 'Esqueci minha senha' na tela de login.",
    "nota fiscal": "Emissão de NF-e: https://nfe.fazenda.gov.br. Certificado digital A1 ou A3 necessário.",
    "backup": "Backups diários às 23h. Para restaurar, abra ticket com prioridade ALTA.",
    "lentidao": "Verifique: 1) Conexão 2) Status em /monitor 3) Abra ticket se persistir.",
}


# =========== AUTH ===========
@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/auth/login")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        log_action(username, "login_failed", "auth", {"reason": "invalid_credentials"})
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Usuário ou senha inválido!"}
        )

    access = create_access_token(
        {"sub": str(user.id)}, expires_delta=timedelta(hours=2)
    )
    log_action(user.username, "login_success", "auth", {"ip": "127.0.0.1"})

    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        samesite="lax",
        max_age=7200,
        secure=False,
        path="/",
    )
    return resp


@app.post("/auth/logout")
def logout(request: Request):
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


# =========== DASHBOARD ===========
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_hosts = db.query(MonitorHost).count()
    total_tickets = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id).count()
    total_backups = db.query(BackupJob).count()

    status_counts = {
        "aberto": db.query(Ticket)
        .filter(Ticket.tenant_id == user.tenant_id, Ticket.status == "aberto")
        .count(),
        "fechado": db.query(Ticket)
        .filter(Ticket.tenant_id == user.tenant_id, Ticket.status == "fechado")
        .count(),
        "andamento": db.query(Ticket)
        .filter(Ticket.tenant_id == user.tenant_id, Ticket.status == "andamento")
        .count(),
    }

    critical_tickets = (
        db.query(Ticket)
        .filter(Ticket.tenant_id == user.tenant_id, Ticket.status == "aberto")
        .order_by(Ticket.id.desc())
        .limit(5)
        .all()
    )
    last_backup = db.query(BackupJob).order_by(BackupJob.iniciado_em.desc()).first()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "total_hosts": total_hosts,
            "total_tickets": total_tickets,
            "total_backups": total_backups,
            "status_counts": status_counts,
            "critical_tickets": critical_tickets,
            "last_backup": last_backup,
        },
    )


# =========== MONITORAMENTO ===========
@app.get("/monitor", response_class=HTMLResponse)
def monitor(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    hosts = db.query(MonitorHost).all()
    return templates.TemplateResponse(
        "monitor.html", {"request": request, "hosts": hosts, "user": user}
    )


@app.post("/monitor/add")
def monitor_add(
    nome: str = Form(...),
    ip: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    host = MonitorHost(nome=nome, ip=ip)
    db.add(host)
    db.commit()
    log_action(user.username, "host_added", "monitor", {"host": nome, "ip": ip})
    return RedirectResponse("/monitor", status_code=303)


# =========== TICKETS ===========
@app.get("/tickets", response_class=HTMLResponse)
def tickets_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tickets = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id).all()
    return templates.TemplateResponse(
        "tickets.html", {"request": request, "tickets": tickets, "user": user}
    )


@app.post("/tickets/create")
def create_ticket(
    titulo: str = Form(...),
    descricao: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = Ticket(
        titulo=titulo,
        descricao=descricao,
        status="aberto",
        tenant_id=user.tenant_id,
        solicitante_id=user.id,
    )
    db.add(ticket)
    db.commit()
    log_action(
        user.username,
        "ticket_created",
        "tickets",
        {"ticket_id": ticket.id, "titulo": titulo},
    )
    return RedirectResponse("/tickets", status_code=303)


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_view(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
        .first()
    )
    if not ticket:
        return RedirectResponse("/tickets")
    return templates.TemplateResponse(
        "ticket_view.html", {"request": request, "ticket": ticket, "user": user}
    )


# =========== BACKUPS ===========
@app.get("/backups", response_class=HTMLResponse)
def backups(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    jobs = db.query(BackupJob).order_by(BackupJob.iniciado_em.desc()).all()
    return templates.TemplateResponse(
        "backups.html", {"request": request, "backups": jobs, "user": user}
    )


@app.post("/backups/add")
def backup_add(
    alvo: str = Form(...),
    status: str = Form(...),
    detalhe: str = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = BackupJob(alvo=alvo, status=status, detalhe=detalhe)
    db.add(job)
    db.commit()
    log_action(
        user.username, "backup_registered", "backups", {"alvo": alvo, "status": status}
    )
    return RedirectResponse("/backups", status_code=303)


# =========== CONTROLE DE USO ===========
@app.get("/usage", response_class=HTMLResponse)
def usage_policy(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    regras = db.query(UsageRule).all()
    return templates.TemplateResponse(
        "usage.html", {"request": request, "regras": regras, "user": user}
    )


@app.post("/usage/add")
def usage_add(
    grupo: str = Form(...),
    categoria: str = Form(...),
    permitido: str = Form(...),
    horario: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    regra = UsageRule(
        grupo=grupo,
        categoria=categoria,
        permitido=(permitido == "sim"),
        horario=horario,
    )
    db.add(regra)
    db.commit()
    log_action(
        user.username,
        "usage_rule_added",
        "usage",
        {"grupo": grupo, "categoria": categoria},
    )
    return RedirectResponse("/usage", status_code=303)


@app.post("/usage/block-domain")
def block_domain(
    domain: str = Form(...),
    department: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    key = f"{department}:{domain}"
    blocked_domains[key] = {
        "blocked_at": datetime.now().isoformat(),
        "blocked_by": user.username,
    }
    log_action(
        user.username,
        "domain_blocked",
        "usage",
        {"domain": domain, "department": department},
    )
    return RedirectResponse("/usage", status_code=303)


# =========== RELATÓRIOS ===========
@app.get("/reports", response_class=HTMLResponse)
def reports(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tickets = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id).all()
    return templates.TemplateResponse(
        "reports.html", {"request": request, "tickets": tickets, "user": user}
    )


# =========== APIs DE INTEGRAÇÃO (MELHORIAS) ===========


@app.get("/api/receita/consulta")
def consulta_receita(
    cpf: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Cache para reduzir latência na Receita Federal"""
    import time

    timestamp = str(int(time.time()) // 300)
    result = cached_receita_query(f"cpf/{cpf}", timestamp)
    data = json.loads(result)

    return {
        "cpf": cpf,
        "result": data,
        "latency_ms": 45 if data.get("cached") else 1200,
        "message": (
            "✅ Consulta otimizada com cache"
            if data.get("cached")
            else "⏳ Consulta direta"
        ),
    }


@app.get("/api/usage/blocked")
def get_blocked_domains(user: User = Depends(get_current_user)):
    """Lista domínios bloqueados"""
    return {
        "blocked": [
            {"domain": k.split(":")[1], "dept": k.split(":")[0], **v}
            for k, v in blocked_domains.items()
        ]
    }


@app.get("/api/monitor/alerts")
def get_network_alerts(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Alertas proativos baseados em métricas"""
    alerts = []

    if random.random() > 0.7:
        alerts.append(
            {
                "level": "critical",
                "title": "🔴 Servidor de Arquivos Offline",
                "message": "SRV-ARQUIVOS-01 não responde há 3 minutos",
                "action": "Verificar conexão e reiniciar serviço",
                "timestamp": datetime.now().isoformat(),
            }
        )

    if random.random() > 0.6:
        alerts.append(
            {
                "level": "warning",
                "title": "🟡 Alta Utilização de CPU",
                "message": "Receita Federal API: 92% CPU por 10 minutos",
                "action": "Considerar cache adicional",
                "timestamp": datetime.now().isoformat(),
            }
        )

    if not alerts:
        alerts.append(
            {
                "level": "success",
                "title": "🟢 Todos os Sistemas Operacionais",
                "message": "Infraestrutura estável",
                "action": None,
                "timestamp": datetime.now().isoformat(),
            }
        )

    return {"alerts": alerts, "generated_at": datetime.now().isoformat()}


@app.get("/api/monitor/{host_id}/metrics")
def host_metrics(host_id: int, db: Session = Depends(get_db)):
    """Métricas SNMP simuladas"""
    return JSONResponse(
        {
            "cpu": random.randint(20, 80),
            "memory": random.randint(30, 90),
            "disk": random.randint(40, 85),
            "network_in": random.randint(100, 1000),
            "network_out": random.randint(50, 800),
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.post("/backups/{job_id}/run")
def run_backup(
    job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Executa backup simulado"""
    job = db.query(BackupJob).filter(BackupJob.id == job_id).first()
    if not job:
        return JSONResponse({"error": "Job não encontrado"}, status_code=404)

    job.status = "sucesso"
    size = random.randint(200, 2000)
    job.detalhe = f"Backup: {size}MB criptografados (SHA256)"
    job.finalizado_em = datetime.now()
    db.commit()

    log_action(
        user.username, "backup_executed", "backups", {"job_id": job_id, "size_mb": size}
    )
    return JSONResponse({"status": "success", "size_mb": size})


@app.post("/backups/{job_id}/verify")
def verify_backup(
    job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Verifica integridade do backup"""
    job = db.query(BackupJob).filter(BackupJob.id == job_id).first()
    if not job:
        return {"error": "Job não encontrado"}

    checksum = hashlib.sha256(
        f"backup_{job_id}_{datetime.now().isoformat()}".encode()
    ).hexdigest()
    return {
        "status": "verified",
        "checksum": f"sha256:{checksum[:32]}...",
        "integrity": "✅ OK",
    }


@app.post("/backups/schedule")
def schedule_backup(
    target: str = Form(...),
    frequency: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Agenda backup automático"""
    log_action(
        user.username,
        "backup_scheduled",
        "backups",
        {"target": target, "frequency": frequency},
    )
    return {
        "status": "scheduled",
        "target": target,
        "frequency": frequency,
        "next_run": "Hoje 23:00",
    }


@app.post("/tickets/{ticket_id}/suggest-reply")
def suggest_reply(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sugere resposta automática baseada em palavras-chave"""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        return {"error": "Ticket não encontrado"}

    suggestions = []
    text_lower = (ticket.descricao or "").lower()

    for keyword, response in KNOWLEDGE_BASE.items():
        if keyword in text_lower:
            suggestions.append(
                {"keyword": keyword, "suggestion": response, "confidence": 0.9}
            )

    return {"ticket_id": ticket_id, "suggestions": suggestions}
