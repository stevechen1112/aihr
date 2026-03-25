from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.core import security
from app.core.cookie_auth import extract_access_token
from app.crud import crud_user
from app.db.session import SessionLocal, apply_rls_context
from app.models.user import User
from app.schemas.token import TokenPayload

# Keep OAuth2 scheme for OpenAPI docs; actual extraction uses cookie_auth
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    auto_error=False,
)


def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    _bearer: Optional[str] = Depends(reusable_oauth2),
) -> User:
    # Extract token from HttpOnly cookie first, then Authorization header
    token = extract_access_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = crud_user.get_by_email(db, email=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    apply_rls_context(
        db,
        tenant_id=getattr(user, "tenant_id", None),
        bypass=getattr(user, "is_superuser", False),
    )
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_user_lazy_db(
    request: Request,
    _bearer: Optional[str] = Depends(reusable_oauth2),
) -> User:
    token = extract_access_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

    db = SessionLocal()
    try:
        user = crud_user.get_by_email(db, email=token_data.sub)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        apply_rls_context(
            db,
            tenant_id=getattr(user, "tenant_id", None),
            bypass=getattr(user, "is_superuser", False),
        )
        return user
    finally:
        db.close()


def get_current_active_user_lazy_db(
    current_user: User = Depends(get_current_user_lazy_db),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
