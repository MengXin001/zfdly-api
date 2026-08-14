from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from sqlmodel import select

from api.deps import CurrentAdmin, SessionDep
from models import Album, AlbumCoverUpdate, AlbumCreate, AlbumPublic, AlbumUpdate, Photo, PhotoPublic

router = APIRouter(prefix="/albums", tags=["albums"])
AlbumId = Annotated[str, Path(pattern=r"^[a-zA-Z0-9_-]{1,100}$")]


def get_album_cover(album: Album, session: SessionDep) -> Photo | None:
    cover = session.get(Photo, album.cover_photo_id) if album.cover_photo_id else None
    if cover is not None and (cover.album_id != album.id or cover.status != "active"):
        return None
    return cover


def public_album(album: Album, cover: Photo | None) -> AlbumPublic:
    return AlbumPublic(
        id=album.id,
        title=album.title,
        description=album.description,
        introDetail=album.introDetail,
        keywords=album.keywords,
        videoTitle=album.videoTitle,
        videoUrl=album.videoUrl,
        cover=PhotoPublic.model_validate(cover) if cover else None,
        created_at=album.created_at,
    )


@router.get("", response_model=list[AlbumPublic])
def list_albums(session: SessionDep) -> list[AlbumPublic]:
    albums = session.exec(select(Album).order_by(Album.created_at.desc())).all()
    cover_ids = {album.cover_photo_id for album in albums if album.cover_photo_id is not None}
    covers_by_id = {
        photo.id: photo
        for photo in session.exec(select(Photo).where(Photo.id.in_(cover_ids), Photo.status == "active")).all()
    }
    return [
        public_album(
            album,
            cover if (cover := covers_by_id.get(album.cover_photo_id)) and cover.album_id == album.id else None,
        )
        for album in albums
    ]


@router.get("/{album_id}", response_model=AlbumPublic)
def get_album(album_id: AlbumId, session: SessionDep) -> AlbumPublic:
    album = session.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    return public_album(album, get_album_cover(album, session))


@router.post("", response_model=AlbumPublic, status_code=status.HTTP_201_CREATED)
def create_album(body: AlbumCreate, session: SessionDep, _: CurrentAdmin) -> AlbumPublic:
    if session.get(Album, body.id):
        raise HTTPException(status_code=409, detail="相册已存在")
    album = Album.model_validate(body)
    session.add(album)
    session.commit()
    session.refresh(album)
    return public_album(album, None)


@router.patch("/{album_id}", response_model=AlbumPublic)
def update_album(album_id: AlbumId, body: AlbumUpdate, session: SessionDep, _: CurrentAdmin) -> AlbumPublic:
    album = session.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    album.sqlmodel_update(body.model_dump(exclude_unset=True))
    session.add(album)
    session.commit()
    session.refresh(album)
    return public_album(album, get_album_cover(album, session))


@router.patch("/{album_id}/cover", response_model=AlbumPublic)
def update_album_cover(
    album_id: AlbumId,
    body: AlbumCoverUpdate,
    session: SessionDep,
    _: CurrentAdmin,
) -> AlbumPublic:
    album = session.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    if body.photo_id is not None:
        photo = session.get(Photo, body.photo_id)
        if photo is None or photo.status != "active" or photo.album_id != album.id:
            raise HTTPException(status_code=422, detail="封面图片必须属于该相册且处于有效状态")
    album.cover_photo_id = body.photo_id
    session.add(album)
    session.commit()
    session.refresh(album)
    return public_album(album, get_album_cover(album, session))


@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(album_id: AlbumId, session: SessionDep, _: CurrentAdmin) -> None:
    album = session.get(Album, album_id)
    if album is None:
        raise HTTPException(status_code=404, detail="相册不存在")
    if session.exec(select(Photo.id).where(Photo.album_id == album_id)).first() is not None:
        raise HTTPException(status_code=409, detail="相册内容不为空，无法删除")
    session.delete(album)
    session.commit()
