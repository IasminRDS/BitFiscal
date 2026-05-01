#Migrar dados
from app.db import SessionLocal, engine
from app.models import Base
import psycopg2
import os

print("Conecte ao PostgreSQL e use pg_dump ou importe via pandas.")
