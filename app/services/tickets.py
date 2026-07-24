from sqlalchemy.orm import Session
from app.models import Ticket


def get_all_tickets(db: Session):
    return db.query(Ticket).order_by(Ticket.criado_em.desc()).all()


def create_ticket(db: Session, titulo: str, descricao: str, tenant_id: int, solicitante_id: int = None):
    ticket = Ticket(
        titulo=titulo,
        descricao=descricao,
        tenant_id=tenant_id,
        solicitante_id=solicitante_id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def update_ticket_status(db: Session, ticket_id: int, status: str):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket:
        ticket.status = status
        db.commit()
    return ticket
