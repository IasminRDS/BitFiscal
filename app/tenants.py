from fastapi import APIRouter, Request, Depends, Form
from sqlalchemy.orm import Session
from .db import get_db
from .models import Tenant

router = APIRouter()


@router.get("/tenants")
def list_tenants(request: Request, db: Session = Depends(get_db)):
    tenants = db.query(Tenant).all()
    return {"tenants": [t.name for t in tenants]}


@router.post("/tenants/add")
def add_tenant(name: str = Form(...), db: Session = Depends(get_db)):
    t = Tenant(name=name)
    db.add(t)
    db.commit()
    return {"ok": True}
