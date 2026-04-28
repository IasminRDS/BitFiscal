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
)
from .models import User
from .db import Base, engine, get_db
from .config import settings

app = FastAPI()
Base.metadata.create_all(bind=engine)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


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
        # retorna o formulário com erro
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Usuário ou senha inválido!"}
        )
    access = create_access_token({"sub": str(user.id)})
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie("access_token", access, httponly=True, samesite="lax")
    return resp


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "dashboard.html", {"request": request, "user": user}
    )


# =========== TICKETS ROTAS ===========


@app.get("/tickets", response_class=HTMLResponse)
def tickets(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Todos os tickets do tenant do usuário
    tickets = db.query(Ticket).filter(Ticket.tenant_id == user.tenant_id).all()
    return templates.TemplateResponse(
        "tickets.html", {"request": request, "tickets": tickets, "user": user}
    )


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


@app.post("/tickets/{ticket_id}/comentar")
def comentar(
    ticket_id: int,
    texto: str = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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
    fname, path = save_upload_file(file)
    anexo = TicketAttachment(
        ticket_id=ticket_id, filename=file.filename, path=path, uploaded_by_id=user.id
    )
    db.add(anexo)
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
        return RedirectResponse("/tickets")
    return FileResponse(
        anexo.path, media_type="application/octet-stream", filename=anexo.filename
    )


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
        # Exemplo de checagem de workflow: só gestor/admin pode fechar
        if status == "fechado" and user.role not in ("admin", "gestor"):
            return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
        ticket.status = status
        db.commit()
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
