import logging
from fastapi import (
    FastAPI,
    Request,
    Depends,
    Form,
    UploadFile,
    File,
    HTTPException,
    Query,
)
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import desc
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.background import BackgroundScheduler
from app.config import settings

from .auth import get_current_user, verify_password, create_access_token
from .models import (
    User,
    Ticket,
    TicketComment,
    TicketAttachment,
    BackupJob,
    UsageRule,
    MonitorHost,
)
from .db import Base, engine, get_db, SessionLocal
from .services.files import save_upload_file_secure
from .services import (
    monitor,
    backup,
    usage,
    base_conhecimento,
    reports as report_service,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="BitFiscal", version="2.0")
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

Base.metadata.create_all(bind=engine)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


#Seed_admin
def seed_admin():
    import os
    from .auth import get_password_hash
    from .models import Tenant

    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "admin")
    # Escotilha de reset: se ADMIN_RESET for verdadeiro, garante que a senha do
    # admin seja sempre a configurada (útil em demos/deploy com banco herdado).
    reset = os.getenv("ADMIN_RESET", "false").lower() in ("1", "true", "yes")

    db = SessionLocal()
    try:
        # Garante o tenant padrão
        if not db.query(Tenant).filter(Tenant.id == 1).first():
            db.add(Tenant(id=1, name="CONTECH"))
            db.commit()

        admin = db.query(User).filter(User.username == username).first()
        if not admin:
            db.add(
                User(
                    username=username,
                    password_hash=get_password_hash(password),
                    role="admin",
                    tenant_id=1,
                )
            )
            db.commit()
        elif reset:
            admin.password_hash = get_password_hash(password)
            admin.is_active = True
            db.commit()
    finally:
        db.close()


seed_admin()

#Scheduler
scheduler = BackgroundScheduler()


@app.on_event("startup")
def start_scheduler():
    def monitor_job():
        db = SessionLocal()
        try:
            monitor.atualizar_todos_hosts(db)
        finally:
            db.close()

    def backup_job():
        db = SessionLocal()
        try:
            backup.executar_backups(db)
        finally:
            db.close()

    scheduler.add_job(
        monitor_job, "interval", seconds=settings.MONITOR_INTERVAL, id="monitor"
    )
    scheduler.add_job(backup_job, "cron", hour=2, minute=0, id="backup")
    scheduler.start()


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()


#Error_handlers
@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    errors = [
        {"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        {"detail": "Dados inválidos", "errors": errors}, status_code=422
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse({"detail": "Muitas requisições"}, status_code=429)


#Rota raiz
@app.get("/")
async def root():
    return RedirectResponse("/login")


#Auth_routes
@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/auth/login")
@limiter.limit("5/15minutes")
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Usuário ou senha inválidos"}
        )
    token = create_access_token({"sub": str(user.id)})
    resp = RedirectResponse("/dashboard", status_code=303)
    resp.set_cookie(
        "access_token",
        token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    logger.info(f"Login bem-sucedido: {username}")
    return resp


@app.post("/auth/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


@app.get("/auth/logout")
def logout_get():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


#Dashboard
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
        "andamento": db.query(Ticket)
        .filter(Ticket.tenant_id == user.tenant_id, Ticket.status == "andamento")
        .count(),
        "fechado": db.query(Ticket)
        .filter(Ticket.tenant_id == user.tenant_id, Ticket.status == "fechado")
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


#Tickets
@app.get("/tickets", response_class=HTMLResponse)
def tickets_list(
    request: Request,
    status: str = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id)
    if status and status in ["aberto", "andamento", "pendente_aprovacao", "fechado"]:
        query = query.filter(Ticket.status == status)
    total = query.count()
    tickets = query.order_by(desc(Ticket.criado_em)).offset(skip).limit(limit).all()
    return templates.TemplateResponse(
        "tickets.html",
        {
            "request": request,
            "tickets": tickets,
            "user": user,
            "total": total,
            "page": skip // limit + 1,
            "pages": max(1, (total + limit - 1) // limit),
        },
    )


@app.post("/tickets/create")
def create_ticket(
    titulo: str = Form(...),
    descricao: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(titulo) < 3 or len(titulo) > 150:
        raise HTTPException(400, "Título inválido")
    if len(descricao) < 10 or len(descricao) > 2000:
        raise HTTPException(400, "Descrição inválida")
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
        .filter(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
        .first()
    )
    if not ticket:
        raise HTTPException(404, "Ticket não encontrado")
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
        raise HTTPException(404, "Ticket não encontrado")
    if not texto or len(texto) > 1000:
        raise HTTPException(400, "Comentário inválido")
    db.add(TicketComment(ticket_id=ticket_id, autor_id=user.id, texto=texto))
    db.commit()
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.post("/tickets/{ticket_id}/anexar")
async def anexar(
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
        raise HTTPException(404)
    fname, path = await save_upload_file_secure(file)
    db.add(
        TicketAttachment(
            ticket_id=ticket_id, filename=fname, path=path, uploaded_by_id=user.id
        )
    )
    db.commit()
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.post("/tickets/{ticket_id}/status")
def alterar_status(
    ticket_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if status not in ["aberto", "andamento", "pendente_aprovacao", "fechado"]:
        raise HTTPException(400)
    ticket = (
        db.query(Ticket)
        .filter(Ticket.id == ticket_id, Ticket.tenant_id == user.tenant_id)
        .first()
    )
    if not ticket:
        raise HTTPException(404)
    if status == "fechado" and user.role not in ("admin", "gestor"):
        raise HTTPException(403)
    ticket.status = status
    db.commit()
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.get("/download/{anexo_id}")
def download_anexo(
    anexo_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    anexo = (
        db.query(TicketAttachment)
        .join(Ticket)
        .filter(TicketAttachment.id == anexo_id, Ticket.tenant_id == user.tenant_id)
        .first()
    )
    if not anexo:
        raise HTTPException(404)
    return FileResponse(anexo.path, filename=anexo.filename)


#Monitor
@app.get("/monitor", response_class=HTMLResponse)
def monitor_page(request: Request, db: Session = Depends(get_db)):
    hosts = db.query(MonitorHost).order_by(MonitorHost.nome).all()
    return templates.TemplateResponse(
        "monitor.html",
        {
            "request": request,
            "hosts": hosts,
            "settings": settings,
        },
    )


@app.post("/monitor/add")
def monitor_add(
    nome: str = Form(...),
    ip: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not nome or not ip:
        raise HTTPException(400)
    if db.query(MonitorHost).filter(MonitorHost.ip == ip).first():
        raise HTTPException(400, "IP já cadastrado")
    host = MonitorHost(nome=nome, ip=ip)
    db.add(host)
    db.commit()
    return RedirectResponse("/monitor", status_code=303)


#Backups
@app.get("/backups", response_class=HTMLResponse)
def backups_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    jobs = db.query(BackupJob).order_by(desc(BackupJob.iniciado_em)).limit(50).all()
    return templates.TemplateResponse(
        "backups.html", {"request": request, "backups": jobs, "user": user}
    )


@app.post("/backups/executar")
def executar_backup_agora(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if user.role not in ("admin", "gestor"):
        raise HTTPException(403)
    backup.executar_backups(db)
    return RedirectResponse("/backups", status_code=303)


@app.post("/backups/add")
def registrar_backup(
    alvo: str = Form(...),
    status: str = Form(...),
    detalhe: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role not in ("admin", "gestor"):
        raise HTTPException(403)
    if not alvo or len(alvo) > 100:
        raise HTTPException(400, "Alvo inválido")
    if status not in ("sucesso", "ok", "falha", "parcial", "pendente"):
        raise HTTPException(400, "Status inválido")
    db.add(BackupJob(alvo=alvo, status=status, detalhe=detalhe[:500]))
    db.commit()
    return RedirectResponse("/backups", status_code=303)


# Usage (controle de uso)
@app.get("/usage", response_class=HTMLResponse)
def usage_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dominios = usage.read_blocked_domains()
    regras = db.query(UsageRule).all()
    return templates.TemplateResponse(
        "usage.html",
        {"request": request, "dominios": dominios, "regras": regras, "user": user},
    )


@app.post("/usage/adicionar")
def add_domain(
    dominio: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dominios = usage.read_blocked_domains()
    if dominio not in dominios:
        dominios.append(dominio.strip())
        usage.write_blocked_domains(dominios)
        usage.apply_hosts_block(dominios)
    return RedirectResponse("/usage", status_code=303)


@app.post("/usage/remover")
def remove_domain(
    dominio: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dominios = usage.read_blocked_domains()
    if dominio in dominios:
        dominios.remove(dominio)
        usage.write_blocked_domains(dominios)
        usage.apply_hosts_block(dominios)
    return RedirectResponse("/usage", status_code=303)


@app.post("/usage/regra")
def add_rule(
    grupo: str = Form(...),
    categoria: str = Form(...),
    permitido: str = Form(...),
    horario: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db.add(
        UsageRule(
            grupo=grupo,
            categoria=categoria,
            permitido=(permitido == "sim"),
            horario=horario,
        )
    )
    db.commit()
    return RedirectResponse("/usage", status_code=303)


#Users (gestão de usuários — admin)
@app.get("/users", response_class=HTMLResponse)
def users_list(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(403, "Apenas administradores")
    users = (
        db.query(User)
        .filter(User.tenant_id == user.tenant_id)
        .order_by(User.username)
        .all()
    )
    return templates.TemplateResponse(
        "users.html", {"request": request, "users": users, "user": user}
    )


@app.post("/users/add")
def users_add(
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form("operador"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(403, "Apenas administradores")
    from .auth import get_password_hash

    if len(username) < 3 or len(username) > 50:
        raise HTTPException(400, "Usuário inválido")
    if len(password) < 6:
        raise HTTPException(400, "Senha deve ter ao menos 6 caracteres")
    if role not in ("admin", "gestor", "operador"):
        raise HTTPException(400, "Papel inválido")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "Usuário já existe")
    db.add(
        User(
            username=username,
            password_hash=get_password_hash(password),
            role=role,
            tenant_id=user.tenant_id,
        )
    )
    db.commit()
    return RedirectResponse("/users", status_code=303)


#FAQ
@app.get("/faq", response_class=HTMLResponse)
def faq_page(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("faq.html", {"request": request, "user": user})


@app.post("/faq")
def faq_search(
    request: Request, question: str = Form(...), user: User = Depends(get_current_user)
):
    answer = base_conhecimento.find_answer(question)
    return templates.TemplateResponse(
        "faq.html",
        {"request": request, "question": question, "answer": answer, "user": user},
    )


#Reports
@app.get("/reports", response_class=HTMLResponse)
def reports_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tickets = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id).all()
    return templates.TemplateResponse(
        "reports.html", {"request": request, "tickets": tickets, "user": user}
    )


@app.get("/reports/csv")
def download_csv(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tickets = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id).all()
    csv_content = report_service.tickets_csv(tickets)
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        csv_content, headers={"Content-Disposition": "attachment; filename=tickets.csv"}
    )


@app.get("/reports/pdf")
def download_pdf(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    from fastapi.responses import Response

    tickets = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id).all()
    pdf = report_service.tickets_pdf(tickets)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tickets.pdf"},
    )


@app.get("/reports/excel")
def download_excel(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    from fastapi.responses import Response

    tickets = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id).all()
    xlsx = report_service.tickets_excel(tickets)
    return Response(
        xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=tickets.xlsx"},
    )


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0"}
