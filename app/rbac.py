from fastapi import Depends, HTTPException, status
from .auth import get_current_user
from .models import User


def require_role(*roles: str):
    """
    Dependência FastAPI que exige que o usuário autenticado possua
    um dos papéis (roles) informados. Uso:

        @app.get("/admin", dependencies=[Depends(require_role("admin"))])
        def admin_page(): ...

        # Ou como parâmetro de função:
        @app.get("/gestao")
        def gestao(user: User = Depends(require_role("admin", "gestor"))):
            ...
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Requer papel: {', '.join(roles)}.",
            )
        return user

    return checker


# Atalhos prontos para uso
require_admin = require_role("admin")
require_gestor = require_role("admin", "gestor")
require_operador = require_role("admin", "gestor", "operador")
