from passlib.context import CryptContext
from app.db import SessionLocal, engine, Base
from app.models import User

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"], pbkdf2_sha256__default_rounds=29000
)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

db.query(User).filter(User.username == "admin").delete()
db.commit()

admin = User(
    username="admin",
    password_hash=pwd_context.hash("Admin123!"),
    tenant_id=1,
    role="admin",
)
db.add(admin)
db.commit()

print("✅ Usuário 'admin' criado com senha 'Admin123!'")
db.close()
