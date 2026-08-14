from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from sqlmodel import select

from api.deps import CurrentAdmin, SessionDep
from models import Album, AlbumCreate, AlbumPublic, AlbumUpdate, Photo

router = APIRouter(prefix="/albums", tags=["albums"])
AlbumId = Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,100}$")]


def public_album(album: Album) -> AlbumPublic:
    return AlbumPublic.model_validate(album)


@router.get("", response_model=list[AlbumPublic])
def list_albums(session: SessionDep) -> list[AlbumPublic]:
    return [public_album(album) for album in session.exec(select(Album).order_by(Album.created_at.desc())).all()]


@router.get("/{album_id}", response_model=AlbumPublic)
def get_album(album_id: AlbumId, session: SessionDep) -> AlbumPublic:
    album = session.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    return public_album(album)


@router.post("", response_model=AlbumPublic, status_code=status.HTTP_201_CREATED)
def create_album(body: AlbumCreate, session: SessionDep, _: CurrentAdmin) -> AlbumPublic:
    if session.get(Album, body.id):
        raise HTTPException(status_code=409, detail="相册已存在")
    album = Album.model_validate(body)
    session.add(album)
    session.commit()
    session.refresh(album)
    return public_album(album)


@router.patch("/{album_id}", response_model=AlbumPublic)
def update_album(album_id: AlbumId, body: AlbumUpdate, session: SessionDep, _: CurrentAdmin) -> AlbumPublic:
    album = session.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    album.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.add(album)
    session.commit()
    session.refresh(album)
    return public_album(album)


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(album_id: AlbumId, session: SessionDep, _: CurrentAdmin) -> None:
    album = session.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    if session.exec(select(Photo.id).where(Photo.album_id == album_id)).first() is not None:
        raise HTTPException(status_code=409, detail="相册内容不为空，无法删除")
    session.delete(album)
    session.commit()
