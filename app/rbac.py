from fastapi import Request
from .auth import get_user_from_request


def require_role(role: str):
    def deco(request: Request):
        user = get_user_from_request(request)
        if not user or user.role != role:
            return False
        return True

    return deco
