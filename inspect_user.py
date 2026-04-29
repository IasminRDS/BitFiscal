# inspect_user.py
from app.models import User
from app.db import engine

print("📋 Colunas da tabela 'users':")
for column in User.__table__.columns:
    print(
        f"  • {column.name:20} | type={column.type} | nullable={column.nullable} | pk={column.primary_key}"
    )
