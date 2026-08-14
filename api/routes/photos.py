import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlmodel import func, select

from api.deps import CurrentAdmin, CurrentUser, SessionDep, UploadApprovedUser
from core.config import settings
from models import Album, Photo, PhotoPublic, PhotosPublic, PhotoUpdate

router = APIRouter(prefix="/photos", tags=["photos"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def detect_image_type(data: bytes) -> str | None:
    if len(data) >= 4 and data[:2] == b"\xff\xd8" and data[-2:] == b"\xff\xd9":
        return "jpg"
    if len(data) >= 33 and data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR" and data[-8:-4] == b"IEND":
        return "png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP" and int.from_bytes(data[4:8], "little") + 8 == len(data):
        return "webp"
    return None


def public_photo(photo: Photo) -> PhotoPublic:
    return PhotoPublic.model_validate(photo)


def find_photo(session: SessionDep, photo_id: uuid.UUID) -> Photo:
    photo = session.get(Photo, photo_id)
    if photo is None or photo.status != "active":
        raise HTTPException(status_code=404, detail="图片不存在")
    return photo


@router.get("", response_model=PhotosPublic)
def list_photos(
    session: SessionDep,
    album_id: str | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PhotosPublic:
    statement = select(Photo).where(Photo.status == "active")
    count_statement = select(func.count()).select_from(Photo).where(Photo.status == "active")
    if album_id:
        statement = statement.where(Photo.album_id == album_id)
        count_statement = count_statement.where(Photo.album_id == album_id)
    photos = session.exec(statement.order_by(Photo.created_at.desc()).offset(skip).limit(limit)).all()
    return PhotosPublic(data=[public_photo(photo) for photo in photos], count=session.exec(count_statement).one())


@router.get("/{photo_id}", response_model=PhotoPublic)
def get_photo(photo_id: uuid.UUID, session: SessionDep) -> PhotoPublic:
    return public_photo(find_photo(session, photo_id))


@router.post("", response_model=PhotoPublic, status_code=status.HTTP_201_CREATED)
def upload_photo(
    session: SessionDep,
    current_user: UploadApprovedUser,
    file: Annotated[UploadFile, File()],
    album_id: Annotated[str, Form(pattern=r"^[a-zA-Z0-9_-]{1,100}$")],
    title: Annotated[str, Form(min_length=1, max_length=255)],
    comment: Annotated[str | None, Form(max_length=2000)] = None,
    location: Annotated[str | None, Form(max_length=255)] = None,
) -> PhotoPublic:
    if session.get(Album, album_id) is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    image_type = detect_image_type(data)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件大小必须小于 10MB")
    if image_type is None or file.content_type != IMAGE_TYPES[image_type]:
        raise HTTPException(status_code=415, detail="文件格式不支持")
    photo_id = uuid.uuid4()
    stored_filename = f"{photo_id}.{image_type}"
    upload_path = Path(settings.UPLOAD_DIR) / stored_filename
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(data)
    photo = Photo(id=photo_id, album_id=album_id, user_id=current_user.id, filename=stored_filename, url=f"/uploads/{stored_filename}", title=title, author=current_user.name, comment=comment, location=location)
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return public_photo(photo)


@router.patch("/{photo_id}", response_model=PhotoPublic)
def update_photo(photo_id: uuid.UUID, body: PhotoUpdate, session: SessionDep, current_user: CurrentUser) -> PhotoPublic:
    photo = find_photo(session, photo_id)
    if photo.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="只能编辑自己的照片")
    photo.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.add(photo)
    session.commit()
    session.refresh(photo)
    return public_photo(photo)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(photo_id: uuid.UUID, session: SessionDep, _: CurrentAdmin) -> None:
    photo = find_photo(session, photo_id)
    upload_path = Path(settings.UPLOAD_DIR) / photo.filename
    try:
        os.remove(upload_path)
    except FileNotFoundError:
        pass
    session.delete(photo)
    session.commit()
