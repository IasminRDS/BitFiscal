from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, User, Ticket, BackupJob, UsageRule, MonitorHost

SQLITE_URL = "sqlite:///./contech.db"
POSTGRES_URL = "postgresql+psycopg2://contech:contech@localhost:5432/contech"

sqlite_engine = create_engine(SQLITE_URL)
pg_engine = create_engine(POSTGRES_URL)

Base.metadata.create_all(pg_engine)

SQLiteSession = sessionmaker(bind=sqlite_engine)
PgSession = sessionmaker(bind=pg_engine)

sqlite = SQLiteSession()
pg = PgSession()


def copy(model):
    for row in sqlite.query(model).all():
        pg.merge(row)
    pg.commit()


copy(User)
copy(Ticket)
copy(BackupJob)
copy(UsageRule)
copy(MonitorHost)

print("Migração concluída.")
