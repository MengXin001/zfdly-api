import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlmodel import select

from api.deps import CurrentAdmin, CurrentUser, SessionDep
from api.storage import upload_path_from_url
from core.security import get_password_hash, verify_password
from models import Album, LoginRequest, PasswordUpdate, Photo, RegisterRequest, User, UserAdminUpdate, UserPublic, UserUploadApprovalUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


def public_user(user: User) -> UserPublic:
    return UserPublic.model_validate(user)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(body: RegisterRequest, session: SessionDep) -> UserPublic:
    if session.exec(select(User).where(User.phone == body.phone)).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户已存在")
    user = User(phone=body.phone, name=body.name, password_hash=get_password_hash(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return public_user(user)


@router.post("/login", response_model=UserPublic)
def login(body: LoginRequest, request: Request, session: SessionDep) -> UserPublic:
    user = session.exec(select(User).where(User.phone == body.phone)).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的登陆凭证")
    request.session.clear()
    request.session["user_id"] = str(user.id)
    return public_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> Response:
    request.session.clear()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie("photo_session")
    return response


@router.get("/me", response_model=UserPublic)
def read_me(current_user: CurrentUser) -> UserPublic:
    return public_user(current_user)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def update_my_password(body: PasswordUpdate, session: SessionDep, current_user: CurrentUser) -> None:
    current_user.password_hash = get_password_hash(body.password)
    session.add(current_user)
    session.commit()


@router.get("/users", response_model=list[UserPublic])
def list_users(
    session: SessionDep,
    _: CurrentAdmin,
    pending_upload_approval: Annotated[bool, Query()] = False,
) -> list[UserPublic]:
    statement = select(User).order_by(User.created_at.desc())
    if pending_upload_approval:
        statement = statement.where(User.upload_approved.is_(False), User.is_admin.is_(False))
    return [public_user(user) for user in session.exec(statement).all()]


@router.patch("/users/{user_id}/upload-approval", response_model=UserPublic)
def update_upload_approval(
    user_id: uuid.UUID,
    body: UserUploadApprovalUpdate,
    session: SessionDep,
    _: CurrentAdmin,
) -> UserPublic:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    user.upload_approved = body.upload_approved
    session.add(user)
    session.commit()
    session.refresh(user)
    return public_user(user)


@router.patch("/users/{user_id}", response_model=UserPublic)
def update_user(
    user_id: uuid.UUID,
    body: UserAdminUpdate,
    session: SessionDep,
    current_admin: CurrentAdmin,
) -> UserPublic:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if body.password is not None:
        user.password_hash = get_password_hash(body.password)
    if body.is_admin is not None:
        if user.id == current_admin.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能修改当前登录用户的管理员身份")
        user.is_admin = body.is_admin
    session.add(user)
    session.commit()
    session.refresh(user)
    return public_user(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, session: SessionDep, current_admin: CurrentAdmin) -> None:
    if user_id == current_admin.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能删除当前登录的管理员")
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    photos = session.exec(select(Photo).where(Photo.user_id == user.id)).all()
    for photo in photos:
        if upload_path := upload_path_from_url(photo.url):
            upload_path.unlink(missing_ok=True)
        album = session.get(Album, photo.album_id)
        if album and album.cover_photo_id == photo.id:
            album.cover_photo_id = None
            session.add(album)
        session.delete(photo)
    session.delete(user)
    session.commit()
