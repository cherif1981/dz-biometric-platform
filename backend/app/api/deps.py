"""Dependencies مشتركة — RBAC، الصلاحيات."""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole


def require_role(*allowed_roles: str):
    """
    Dependency factory للتحقق من الدور.
    
    الاستخدام:
        @router.post("/admin-only")
        def admin_endpoint(user: dict = Depends(require_role(UserRole.ADMIN))):
            ...
    """
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        # current_user هو dict لأن security.py يرجع dict
        user_role = current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, "role", None)
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"مطلوب أحد الأدوار: {list(allowed_roles)}",
            )
        return current_user
    return checker


def require_permission(permission: str):
    """
    Dependency factory للتحقق من صلاحية محددة.
    الصلاحيات تُشتق من الدور.
    """
    # مصفوفة الصلاحيات لكل دور
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: {
            "verification:create", "verification:read",
            "ocr:extract", "scan:run",
            "documents:read", "documents:delete",
            "users:manage", "audit:read",
        },
        UserRole.OPERATOR: {
            "verification:create", "verification:read",
            "ocr:extract", "scan:run",
            "documents:read",
        },
        UserRole.VERIFIER: {
            "verification:create", "verification:read",
            "verification:review",
            "documents:read",
        },
        UserRole.AUDITOR: {
            "verification:read",
            "documents:read",
            "audit:read",
        },
    }

    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role") if isinstance(current_user, dict) else getattr(current_user, "role", None)
        user_perms = ROLE_PERMISSIONS.get(user_role, set())
        if permission not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"مطلوب صلاحية: {permission}",
            )
        return current_user
    return checker
