from app.db import SessionLocal
from app.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
db = SessionLocal()

username = "admin"
senha = "admin123"
role = "admin"
tenant_id = 1

# Veja se já existe
user = db.query(User).filter_by(username=username).first()
if not user:
    senha_hash = pwd_context.hash(senha)
    user = User(
        username=username, password_hash=senha_hash, role=role, tenant_id=tenant_id
    )
    db.add(user)
    db.commit()
    print("Usuário admin criado!")
else:
    print("Usuário admin já existe!")
