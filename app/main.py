from fastapi import FastAPI, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .auth import (
    get_current_user,
    verify_password,
    create_access_token,
    save_refresh_token,
    revoke_refresh_token,
)
from .models import (
    User,
    Ticket,
    TicketComment,
    TicketAttachment,
    BackupJob,
    UsageRule,
    MonitorHost,
)
from .db import Base, engine, get_db
from .config import settings
from .services.files import save_upload_file

app = FastAPI()
Base.metadata.create_all(bind=engine)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


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
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuário ou senha inválido!"},
        )
    access = create_access_token({"sub": str(user.id)})
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie("access_token", access, httponly=True, samesite="lax")
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


# =========== TICKETS ===========


@app.get("/tickets", response_class=HTMLResponse)
def tickets_list(
    request: Request,
    status: str = None,
    responsavel: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id)
    if status:
        query = query.filter(Ticket.status == status)
    tickets = query.all()
    return templates.TemplateResponse(
        "tickets.html", {"request": request, "tickets": tickets, "user": user}
    )


@app.get("/tickets/create", response_class=HTMLResponse)
def ticket_create_get(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "tickets.html", {"request": request, "user": user, "tickets": []}
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


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_view(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.tenant_id == user.tenant_id, Ticket.id == ticket_id)
        .first()
    )
    if not ticket:
        return RedirectResponse("/tickets")
    return templates.TemplateResponse(
        "ticket_view.html", {"request": request, "ticket": ticket, "user": user}
    )


@app.post("/tickets/{ticket_id}/comentar")
def comentar(
    ticket_id: int,
    texto: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
        .first()
    )
    if not ticket:
        return RedirectResponse("/tickets", status_code=303)
    comentario = TicketComment(ticket_id=ticket_id, autor_id=user.id, texto=texto)
    db.add(comentario)
    db.commit()
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.post("/tickets/{ticket_id}/anexar")
def anexar(
    ticket_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
        .first()
    )
    if not ticket:
        return RedirectResponse("/tickets", status_code=303)
    fname, path = save_upload_file(file)
    anexo = TicketAttachment(
        ticket_id=ticket_id,
        filename=fname,
        path=path,
        uploaded_by_id=user.id,
    )
    db.add(anexo)
    db.commit()
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.post("/tickets/{ticket_id}/status")
def alterar_status(
    ticket_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
        .first()
    )
    if ticket:
        if status == "fechado" and user.role not in ("admin", "gestor"):
            return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
        ticket.status = status
        db.commit()
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.get("/download/{anexo_id}")
def download_anexo(
    anexo_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    anexo = (
        db.query(TicketAttachment)
        .join(Ticket)
        .filter(
            TicketAttachment.id == anexo_id,
            Ticket.tenant_id == user.tenant_id,
        )
        .first()
    )
    if not anexo:
        return RedirectResponse("/tickets")
    return FileResponse(
        anexo.path,
        media_type="application/octet-stream",
        filename=anexo.filename,
    )


# =========== MONITOR ===========


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
    return RedirectResponse("/backups", status_code=303)


# =========== USAGE ===========


@app.get("/usage", response_class=HTMLResponse)
def usage(
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


# =========== REPORTS ===========


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
