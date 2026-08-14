from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from core.db import engine
from models import User


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, session: SessionDep) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无权限")
    try:
        user = session.get(User, UUID(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效凭证") from exc
    if user is None:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效凭证")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_admin(current_user: CurrentUser) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]


def get_upload_approved_user(current_user: CurrentUser) -> User:
    if not current_user.is_admin and not current_user.upload_approved:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="未通过管理员审核")
    return current_user


UploadApprovedUser = Annotated[User, Depends(get_upload_approved_user)]
