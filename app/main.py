from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pathlib import Path

from app.auth import get_current_user, verify_password, create_access_token
from app.models import User, Ticket, BackupJob, UsageRule, MonitorHost
from app.db import Base, engine, get_db
from app.config import settings

app = FastAPI(title="BITFISCAL", version="1.0.0")
Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")
STATIC_DIR = BASE_DIR / "app" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


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
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Usuário ou senha inválido!"}
        )
    access = create_access_token(
        {"sub": str(user.id)}, expires_delta=timedelta(hours=2)
    )
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie("access_token", access, httponly=True, samesite="lax", max_age=7200)
    return resp


@app.post("/auth/logout")
def logout(request: Request):
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


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
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "total_hosts": total_hosts,
            "total_tickets": total_tickets,
            "total_backups": total_backups,
            "status_counts": status_counts,
        },
    )


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
    return RedirectResponse("/monitor", status_code=303)


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
    return RedirectResponse("/tickets", status_code=303)


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
    return RedirectResponse("/backups", status_code=303)


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
    return RedirectResponse("/usage", status_code=303)


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
