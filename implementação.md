# 📋 GUIA DE IMPLEMENTAÇÃO — CONTECH Melhorado

## ✅ Arquivos a Substituir/Criar

### 1. **Substitua os arquivos existentes:**

```bash
# Fazer backup primeiro
cp app/main.py app/main.py.backup
cp app/models.py app/models.py.backup
cp app/config.py app/config.py.backup
cp app/rbac.py app/rbac.py.backup
cp app/services/files.py app/services/files.py.backup

# Copiar versões melhoradas
cp main_complete.py app/main.py
cp models_complete.py app/models.py
cp config_complete.py app/config.py
cp rbac_complete.py app/rbac.py
cp files_complete.py app/services/files.py
```

### 2. **Criar novo arquivo de segurança:**

```bash
cp security.py app/security.py
```

### 3. **Atualizar requirements.txt:**

```bash
cp requirements_improved.txt requirements.txt
pip install -r requirements.txt
```

### 4. **Criar pasta de testes (se não existir):**

```bash
mkdir -p app/tests
touch app/tests/__init__.py
cp test_auth.py app/tests/test_auth.py
```

---

## 🔧 Variáveis de Ambiente (.env)

### Gerar chaves seguras:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Arquivo .env melhorado:

```bash
# ─── APP ─────────────────────────────────────
APP_NAME=CONTECH Control Center
DEBUG=false

# ─── DATABASE ────────────────────────────────
# PostgreSQL (RECOMENDADO)
DATABASE_URL=postgresql://user:password@localhost:5432/contech_db

# OU SQLite (DEV ONLY)
# DATABASE_URL=sqlite:///./contech.db

# ─── SEGURANÇA ───────────────────────────────
SECRET_KEY=<gerar-com-comando-acima>
JWT_SECRET_KEY=<gerar-com-comando-acima>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
COOKIE_SECURE=true

# ─── ADMIN (mudar em produção!) ──────────────
ADMIN_USER=admin
ADMIN_PASS=<gerar-senha-forte>
```

---

## 🚀 Passos de Implementação

### Passo 1: Atualizar Dependências

```bash
pip install -r requirements.txt
```

### Passo 2: Criar Banco de Dados Novo (com índices)

```bash
# Se usar PostgreSQL:
dropdb contech_db 2>/dev/null || true
createdb contech_db

# Se usar SQLite:
rm contech.db 2>/dev/null || true

# Rodar migrations
python3 -c "from app.db import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Passo 3: Criar Usuário Admin

```bash
python3 create_admin.py
```

### Passo 4: Executar Testes

```bash
pytest app/tests/ -v
```

### Passo 5: Iniciar Aplicação

```bash
uvicorn app.main:app --reload
```

---

## 📊 Checklist de Melhorias Implementadas

- ✅ **Logging estruturado** em todas as rotas
- ✅ **Error handling global** com handlers específicos
- ✅ **Rate limiting** em login (5 tentativas/15 min)
- ✅ **Validação robusta** com Pydantic em POST
- ✅ **Upload seguro** com validação MIME, size limit, chunks
- ✅ **Índices no banco** para performance
- ✅ **Paginação** em todas as listas (skip/limit)
- ✅ **RBAC melhorado** com permissões granulares
- ✅ **Config validada** com checks em produção
- ✅ **Testes unitários** básicos
- ✅ **Isolamento de tenant** em todas as queries
- ✅ **Health check** endpoint

---

## 🔐 Mudanças de Segurança Importantes

### 1. **Validação de Entrada**

Antes:

```python
@app.post("/tickets/create")
def create_ticket(titulo: str = Form(...), descricao: str = Form(...)):
    ticket = Ticket(titulo=titulo, descricao=descricao)  # ❌ Sem validação
```

Depois:

```python
@app.post("/tickets/create")
def create_ticket(titulo: str = Form(...), descricao: str = Form(...)):
    if not titulo or len(titulo) < 3 or len(titulo) > 150:
        raise HTTPException(400, "Título inválido")
    # ✅ Validado
```

### 2. **Upload Seguro**

Antes:

```python
def save_upload_file(upload: UploadFile):
    path = os.path.join(UPLOAD_DIR, uuid4().hex)  # ❌ Sem validação MIME
    with open(path, "wb") as f:
        f.write(upload.file.read())  # ❌ Carrega tudo em RAM
```

Depois:

```python
async def save_upload_file_secure(upload: UploadFile):
    # ✅ Valida extensão, MIME type, tamanho
    # ✅ Lê em chunks (100KB por vez)
    # ✅ Detecta e rejeita files muito grandes
```

### 3. **Rate Limiting**

Antes:

```python
@app.post("/auth/login")
def login_post(...):  # ❌ Sem proteção contra brute force
```

Depois:

```python
@app.post("/auth/login")
@limiter.limit("5/15minutes")  # ✅ 5 tentativas a cada 15 min
def login_post(...):
```

### 4. **Error Handling**

Antes:

```python
@app.get("/tickets")
def tickets_list(...):
    tickets = db.query(Ticket).all()  # ❌ Sem try/except, vai expor erro
    return tickets
```

Depois:

```python
@app.get("/tickets")
def tickets_list(...):
    try:
        query = db.query(Ticket).filter(...)
        tickets = query.offset(skip).limit(limit).all()  # ✅ Com paginação
        return templates.TemplateResponse(...)
    except Exception as e:
        logger.error(f"Erro: {e}")  # ✅ Log estruturado
        raise HTTPException(500, "Erro ao listar tickets")
```

---

## 🧪 Executar Testes

```bash
# Todos os testes
pytest app/tests/ -v

# Testes específicos
pytest app/tests/test_auth.py::TestAuth::test_login_valido -v

# Com cobertura
pytest app/tests/ --cov=app --cov-report=html
```

---

## 📈 Próximos Passos Recomendados

### Fase 1 (Imediato):

- ✅ Implementar tudo acima
- ✅ Executar testes
- ✅ Deploy em staging

### Fase 2 (Próxima semana):

- [ ] Adicionar 2FA (TOTP)
- [ ] Implementar webhooks
- [ ] Cache com Redis
- [ ] Background tasks (Celery)

### Fase 3 (Curto prazo):

- [ ] Monitoring com Prometheus
- [ ] Logs centralizados (ELK)
- [ ] Backup automático
- [ ] Documentação API (Swagger)

---

## ⚠️ CUIDADO: Antes de Produção

```bash
# Verificar configuração de produção
python3 -c "from app.config import settings; settings.validate_production_settings()"

# Isso vai falhar se:
# - DEBUG=True
# - DATABASE_URL usa SQLite
# - Chaves secretas são padrão
```

---

## 🆘 Troubleshooting

### Erro: "Column does not exist"

Você precisa recriar o banco com a nova schema:

```bash
# PostgreSQL
dropdb contech_db && createdb contech_db

# SQLite
rm contech.db

# Criar tabelas com novos índices
python3 -c "from app.db import Base, engine; Base.metadata.create_all(bind=engine)"
```

### Erro: "ImportError: cannot import name 'limiter'"

Certifique-se que instalou slowapi:

```bash
pip install slowapi
```

### Erro: "RateLimitExceeded not handled"

Verifique que o app.py importa corretamente:

```python
from slowapi.errors import RateLimitExceeded
# E adiciona o handler:
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(...):
```

---

## 📚 Documentação Adicional

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Pydantic: https://docs.pydantic.dev/
- pytest: https://docs.pytest.org/
