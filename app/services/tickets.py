from sqlalchemy.orm import Session
from app.models import Ticket


def get_all_tickets(db: Session):
    return db.query(Ticket).order_by(Ticket.created_at.desc()).all()


def create_ticket(db: Session, title: str, description: str):
    ticket = Ticket(title=title, description=description)
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
