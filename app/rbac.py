from fastapi import Depends, HTTPException, status
import logging
from .auth import get_current_user
from .models import User

logger = logging.getLogger(__name__)


# ─── DEFINIÇÃO DE ROLES ──────────────────────────────────────────
ROLE_HIERARCHY = {
    "admin": {"gestor", "operador"},  # Admin pode fazer tudo
    "gestor": {"operador"},  # Gestor pode fazer tudo exceto admin
    "operador": set(),  # Operador tem acesso limitado
}

ROLE_PERMISSIONS = {
    "admin": {
        "create_ticket",
        "read_ticket",
        "update_ticket",
        "delete_ticket",
        "create_user",
        "read_user",
        "update_user",
        "delete_user",
        "manage_backups",
        "manage_monitoring",
        "manage_usage_rules",
        "view_reports",
        "view_audit_logs",
    },
    "gestor": {
        "create_ticket",
        "read_ticket",
        "update_ticket",
        "manage_backups",
        "manage_monitoring",
        "manage_usage_rules",
        "view_reports",
    },
    "operador": {
        "create_ticket",
        "read_ticket",
        "view_reports",
    },
}

def require_role(*roles: str):
    """
    Dependência que exige um dos papéis especificados.

    Uso:
        @app.get("/admin")
        def admin_only(user: User = Depends(require_role("admin"))):
            ...

        @app.get("/gestao")
        def gestor_or_admin(user: User = Depends(require_role("admin", "gestor"))):
            ...
    """

    async def checker(user: User = Depends(get_current_user)) -> User:
        if not user.is_active:
            logger.warning(f"Acesso negado: usuário {user.username} inativo")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário inativo",
            )

        if user.role not in roles:
            logger.warning(
                f"Acesso negado: {user.username} ({user.role}) tentou acessar recurso de {roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Requer papel: {', '.join(roles)}",
            )

        return user

    return checker


def require_permission(permission: str):
    """
    Dependência que exige uma permissão específica.

    Uso:
        @app.delete("/tickets/{id}")
        def delete_ticket(
            ticket_id: int,
            user: User = Depends(require_permission("delete_ticket"))
        ):
            ...
    """

    async def checker(user: User = Depends(get_current_user)) -> User:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário inativo",
            )

        user_permissions = ROLE_PERMISSIONS.get(user.role, set())
        if permission not in user_permissions:
            logger.warning(
                f"Permissão negada: {user.username} ({user.role}) não tem '{permission}'"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissão '{permission}' negada",
            )

        return user

    return checker


def has_role(user: User, *roles: str) -> bool:
    """
    Verifica se um usuário tem um dos papéis.

    Uso:
        if has_role(current_user, "admin", "gestor"):
            # fazer algo
    """
    return user.role in roles and user.is_active


def has_permission(user: User, permission: str) -> bool:
    """
    Verifica se um usuário tem uma permissão específica.

    Uso:
        if has_permission(current_user, "delete_ticket"):
            # deletar ticket
    """
    if not user.is_active:
        return False

    user_permissions = ROLE_PERMISSIONS.get(user.role, set())
    return permission in user_permissions


def can_access_tenant(user: User, tenant_id: int) -> bool:
    """
    Verifica se um usuário pode acessar um tenant específico.

    Uso:
        if not can_access_tenant(current_user, ticket.tenant_id):
            raise HTTPException(403, "Acesso negado")
    """
    return user.tenant_id == tenant_id


# ─── SHORTCUTS (Atalhos prontos) ─────────────────────────────────

require_admin = require_role("admin")
require_gestor = require_role("admin", "gestor")
require_operador = require_role("admin", "gestor", "operador")

require_create_ticket = require_permission("create_ticket")
require_delete_ticket = require_permission("delete_ticket")
require_manage_users = require_permission("delete_user")
require_view_audit = require_permission("view_audit_logs")
