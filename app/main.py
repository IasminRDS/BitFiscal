from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime

from .db import Base, engine, SessionLocal
from .models import Ticket, BackupJob, UsageRule, MonitorHost
from .services.monitor import ping_host

app = FastAPI(title="CONTECH Control Center")

Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# HOME
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return RedirectResponse(url="/monitor")


# MONITOR
@app.get("/monitor", response_class=HTMLResponse)
def monitor(request: Request, db: Session = Depends(get_db)):
    hosts = db.query(MonitorHost).all()
    return templates("monitor.html", request, {"hosts": hosts})


@app.post("/monitor/add")
def add_host(nome: str = Form(...), ip: str = Form(...), db: Session = Depends(get_db)):
    host = MonitorHost(nome=nome, ip=ip)
    db.add(host)
    db.commit()
    return RedirectResponse(url="/monitor", status_code=303)


@app.post("/monitor/ping/{host_id}")
def pingar(host_id: int, db: Session = Depends(get_db)):
    host = db.query(MonitorHost).get(host_id)
    if host:
        status, ms = ping_host(host.ip)
        host.status = status
        host.ultimo_ping_ms = ms
        host.atualizado_em = datetime.utcnow()
        db.commit()
    return RedirectResponse(url="/monitor", status_code=303)


# TICKETS
@app.get("/tickets", response_class=HTMLResponse)
def tickets(request: Request, db: Session = Depends(get_db)):
    dados = db.query(Ticket).order_by(Ticket.criado_em.desc()).all()
    return templates("tickets.html", request, {"tickets": dados})


@app.post("/tickets/add")
def add_ticket(
    canal: str = Form(...),
    cliente: str = Form(...),
    assunto: str = Form(...),
    prioridade: str = Form(...),
    db: Session = Depends(get_db),
):
    ticket = Ticket(
        canal=canal, cliente=cliente, assunto=assunto, prioridade=prioridade
    )
    db.add(ticket)
    db.commit()
    return RedirectResponse(url="/tickets", status_code=303)


# BACKUPS
@app.get("/backups", response_class=HTMLResponse)
def backups(request: Request, db: Session = Depends(get_db)):
    jobs = db.query(BackupJob).order_by(BackupJob.criado_em.desc()).all()
    return templates("backups.html", request, {"backups": jobs})


@app.post("/backups/add")
def add_backup(
    alvo: str = Form(...),
    status: str = Form(...),
    detalhe: str = Form(""),
    db: Session = Depends(get_db),
):
    job = BackupJob(alvo=alvo, status=status, detalhe=detalhe)
    db.add(job)
    db.commit()
    return RedirectResponse(url="/backups", status_code=303)


# USO / REGRAS
@app.get("/usage", response_class=HTMLResponse)
def usage(request: Request, db: Session = Depends(get_db)):
    regras = db.query(UsageRule).all()
    return templates("usage.html", request, {"regras": regras})


@app.post("/usage/add")
def add_rule(
    grupo: str = Form(...),
    categoria: str = Form(...),
    permitido: str = Form(...),
    horario: str = Form(...),
    db: Session = Depends(get_db),
):
    permitido_bool = True if permitido.lower() == "sim" else False
    rule = UsageRule(
        grupo=grupo, categoria=categoria, permitido=permitido_bool, horario=horario
    )
    db.add(rule)
    db.commit()
    return RedirectResponse(url="/usage", status_code=303)


# TEMPLATE HELPER
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def templates(name, request, context):
    return Jinja2Templates(directory="app/templates").TemplateResponse(
        name, {"request": request, **context}
    )
