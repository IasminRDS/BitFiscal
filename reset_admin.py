# reset_admin.py - VERSÃO ADAPTÁVEL
from passlib.context import CryptContext
from app.db import SessionLocal, engine, Base
from app.models import User

# 🔐 Contexto apenas com bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

Base.metadata.create_all(bind=engine)
db = SessionLocal()

print("🗑️  Removendo usuário 'admin' existente...")
db.query(User).filter(User.username == "admin").delete()
db.commit()

print("🔐 Criando novo usuário 'admin'...")

# 🎯 Crie o usuário APENAS com os campos que seu modelo aceita
# Edite esta seção conforme a saída do inspect_user.py:
novo_admin = User(
    username="admin",
    password_hash=pwd_context.hash("Admin123!"),  # ← hash bcrypt válido
    # 🔽 Adicione/remova campos conforme seu modelo:
    # email="admin@local.test",   # ← REMOVA se não existir
    tenant_id=1,  # ← Mantenha se existir
    role="admin",  # ← Mantenha se existir
    # active=True,                # ← Exemplo: adicione se seu modelo tiver
)

db.add(novo_admin)
db.commit()

print("\n✅ SUCESSO!")
print(f"   Login: admin")
print(f"   Senha: Admin123!")
print(f"   Hash: {novo_admin.password_hash[:40]}...")
print("\n🔍 Confirme que o hash começa com '$2b$', '$2a$' ou '$2y$'")

db.close()
input("\nPressione Enter para sair...")
