from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
import secrets

from .db import Base, engine, get_db
from .models import User, RefreshToken
from .config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer(auto_error=False)  # Permite Authorization: Bearer <token>


# -------- Password Helpers --------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


# -------- Tokens: Create & Verify --------
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )


def create_refresh_token():
    return secrets.token_urlsafe(48)


def verify_access_token(token: str):
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# -------- Persistência dos RefreshTokens --------
def save_refresh_token(db: Session, user_id: int, token: str):
    expires = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    rt = RefreshToken(token=token, user_id=user_id, expires_at=expires, revoked=False)
    db.add(rt)
    db.commit()


def revoke_refresh_token(db: Session, token: str):
    rt = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if rt:
        rt.revoked = True
        db.commit()


# -------- Função principal de user autenticado --------
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = None

    # 1. Primeiro tenta Authorization: Bearer <token>
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    # 2. Depois tenta cookie "access_token"
    if not token:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autenticado. Nenhum token fornecido.",
        )
    payload = verify_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
        )
    user_id = payload.get("sub")
    user = db.query(User).get(int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
        )
    return user
