from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import jwt

from app.database.session import get_session
from app.models.users import User
from app.config.config import get_settings

from app.models.groups import Group

def get_current_user_with_permissions(request: Request, session: Session = Depends(get_session)) -> User:
    # First check for the HttpOnly secure cookie
    token = request.cookies.get("fetch_auth_token")

    # Fallback to Authorization header for API compatibility/testing
    if not token:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Authorization Token")
        token = auth_header.split("Bearer ")[1]

    try:
        decoded_token = jwt.decode(token, get_settings().JWT_SECRET_KEY, algorithms=['HS256'])
        email = decoded_token.get('email')
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Token")

    # query user with groups AND permissions loaded eagerly
    query = select(User).where(User.email == email).options(
        selectinload(User.groups).selectinload(Group.permissions)
    )
    user = session.execute(query).scalars().first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


class RequiresPermission:
    """Route dependency that enforces one or more permission codes.

    Mirrors the production (v1.05) ``require_permissions`` model:
      - ``RequiresPermission("perm")``            -> user must have that perm
      - ``RequiresPermission("a", "b")``          -> user must have ALL of them (AND)
      - ``RequiresPermission("a", "b", any_of=True)`` -> user needs ANY of them (OR)

    Apply per-route (never as a router-prefix blanket): reads use read-perms,
    writes use action-perms, and multi-role endpoints use ``any_of=True``.
    """

    def __init__(self, *permission_codes: str, any_of: bool = False):
        if not permission_codes:
            raise ValueError("RequiresPermission requires at least one permission code")
        self.permission_codes = set(permission_codes)
        self.any_of = any_of

    def __call__(self, user: User = Depends(get_current_user_with_permissions)):
        # Flatten permissions (eager-loaded, so no IO here)
        user_permissions = set()
        for group in user.groups:
            for permission in group.permissions:
                user_permissions.add(permission.name)

        if self.any_of:
            ok = bool(self.permission_codes & user_permissions)
        else:
            ok = self.permission_codes.issubset(user_permissions)

        if not ok:
            joiner = "' or '" if self.any_of else "', '"
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: Missing '{joiner.join(sorted(self.permission_codes))}'"
            )
