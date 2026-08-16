import uuid
from datetime import UTC, datetime

from pydantic import Field as PydanticField
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    phone: str = Field(unique=True, index=True, max_length=32)
    name: str = Field(max_length=100)
    password_hash: str
    is_admin: bool = Field(default=False, index=True)
    upload_approved: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    photos: list["Photo"] = Relationship(back_populates="user")


class Album(SQLModel, table=True):
    id: str = Field(primary_key=True, max_length=100)
    title: str = Field(max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    introDetail: str | None = Field(default=None, max_length=5000)
    keywords: str | None = Field(default=None, max_length=1000)
    videoTitle: str | None = Field(default=None, max_length=255)
    videoUrl: str | None = Field(default=None, max_length=512)
    cover_photo_id: uuid.UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    photos: list["Photo"] = Relationship(back_populates="album")


class Photo(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    album_id: str = Field(foreign_key="album.id", index=True, max_length=100)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    filename: str = Field(max_length=255)
    url: str = Field(max_length=512)
    title: str = Field(max_length=255)
    author: str = Field(max_length=100)
    comment: str | None = Field(default=None, max_length=2000)
    location: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    status: str = Field(default="active", index=True, max_length=32)
    user: User | None = Relationship(back_populates="photos")
    album: Album | None = Relationship(back_populates="photos")


class RegisterRequest(SQLModel):
    phone: str = PydanticField(pattern=r"^\+?[0-9]{6,20}$")
    password: str = PydanticField(min_length=8, max_length=128)
    name: str = PydanticField(min_length=1, max_length=100)


class LoginRequest(SQLModel):
    phone: str = PydanticField(pattern=r"^\+?[0-9]{6,20}$")
    password: str = PydanticField(min_length=1, max_length=128)


class UserPublic(SQLModel):
    id: uuid.UUID
    phone: str
    name: str
    is_admin: bool
    upload_approved: bool
    created_at: datetime


class UserUploadApprovalUpdate(SQLModel):
    upload_approved: bool


class UserAdminUpdate(SQLModel):
    password: str | None = PydanticField(default=None, min_length=8, max_length=128)
    is_admin: bool | None = None


class PasswordUpdate(SQLModel):
    password: str = PydanticField(min_length=8, max_length=128)


class UserNameUpdate(SQLModel):
    name: str = PydanticField(min_length=1, max_length=100)
    user_id: uuid.UUID | None = None


class AlbumCreate(SQLModel):
    id: str = PydanticField(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    title: str = PydanticField(min_length=1, max_length=255)
    description: str | None = PydanticField(default=None, max_length=1000)
    introDetail: str | None = PydanticField(default=None, max_length=5000)
    keywords: str | None = PydanticField(default=None, max_length=1000)
    videoTitle: str | None = PydanticField(default=None, max_length=255)
    videoUrl: str | None = PydanticField(default=None, max_length=512)


class AlbumUpdate(SQLModel):
    title: str | None = PydanticField(default=None, min_length=1, max_length=255)
    description: str | None = PydanticField(default=None, max_length=1000)
    introDetail: str | None = PydanticField(default=None, max_length=5000)
    keywords: str | None = PydanticField(default=None, max_length=1000)
    videoTitle: str | None = PydanticField(default=None, max_length=255)
    videoUrl: str | None = PydanticField(default=None, max_length=512)


class PhotoUpdate(SQLModel):
    filename: str | None = PydanticField(default=None, min_length=1, max_length=255)
    title: str | None = PydanticField(default=None, min_length=1, max_length=255)
    author: str | None = PydanticField(default=None, min_length=1, max_length=100)
    comment: str | None = PydanticField(default=None, max_length=2000)
    location: str | None = PydanticField(default=None, max_length=255)


class PhotoPublic(SQLModel):
    id: uuid.UUID
    album_id: str
    user_id: uuid.UUID
    filename: str
    url: str
    title: str
    author: str
    comment: str | None
    location: str | None
    created_at: datetime
    status: str


class AlbumPublic(SQLModel):
    id: str
    title: str
    description: str | None
    introDetail: str | None
    keywords: str | None
    videoTitle: str | None
    videoUrl: str | None
    cover: PhotoPublic | None
    created_at: datetime


class AlbumCoverUpdate(SQLModel):
    photo_id: uuid.UUID | None = None


class PhotosPublic(SQLModel):
    data: list[PhotoPublic]
    count: int
