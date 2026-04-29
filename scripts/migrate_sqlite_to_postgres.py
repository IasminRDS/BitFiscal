# script simples para migrar dados
from app.db import SessionLocal, engine
from app.models import Base
import psycopg2
import os

# Este script é um esqueleto; você precisa adaptar as conexões.
print("Conecte ao PostgreSQL e use pg_dump ou importe via pandas.")
