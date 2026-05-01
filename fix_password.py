from passlib.context import CryptContext
from app.db import SessionLocal, engine, Base
from app.models import User

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"], pbkdf2_sha256__default_rounds=29000
)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("👥 Usuários no banco:")
for u in db.query(User).all():
    print(f"  ID={u.id} | Username={u.username} | Hash={u.password_hash[:60]}...")

username = "admin"
nova_senha = "Admin123!"  # senha temporária

user = db.query(User).filter(User.username == username).first()
if user:
    user.password_hash = pwd_context.hash(nova_senha)
    db.commit()
    print(f"\n✅ Senha de '{username}' atualizada com pbkdf2_sha256!")
    print(f"   Use para login: {username} / {nova_senha}")
else:
    print(f"\n❌ Usuário '{username}' não encontrado.")
    print("💡 Criando novo usuário de teste...")
    from app.models import User as UserModel

    novo = UserModel(
        username="admin",
        email="admin@local.test",
        password_hash=pwd_context.hash("Admin123!"),
        tenant_id=1,
        role="admin",
    )
    db.add(novo)
    db.commit()
    print("✅ Usuário criado! Login: admin / Admin123!")

db.close()
input("\nPressione Enter para sair...")
