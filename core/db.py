import json
from pathlib import Path

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine, select

from core.config import settings
from core.security import get_password_hash
from models import Album, User

sqlite_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=sqlite_connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    if "user" in tables:
        user_columns = {column["name"] for column in inspector.get_columns("user")}
    else:
        user_columns = set()
    if "user" in tables and "upload_approved" not in user_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE user ADD COLUMN upload_approved BOOLEAN NOT NULL DEFAULT 0"))
    if "album" in tables:
        album_columns = {column["name"] for column in inspector.get_columns("album")}
        missing_album_columns = {
            "cover_photo_id": "CHAR(32)",
            "introDetail": "VARCHAR(5000)",
            "keywords": "VARCHAR(1000)",
            "videoTitle": "VARCHAR(255)",
            "videoUrl": "VARCHAR(512)",
        }
        missing_album_columns = {
            name: column_type
            for name, column_type in missing_album_columns.items()
            if name not in album_columns
        }
        if missing_album_columns:
            with engine.begin() as connection:
                for name, column_type in missing_album_columns.items():
                    connection.execute(text(f"ALTER TABLE album ADD COLUMN {name} {column_type}"))


def seed_albums(session: Session) -> None:
    seed_path = Path("data/albums.json")
    if not seed_path.exists():
        return
    albums = json.loads(seed_path.read_text(encoding="utf-8"))
    for album_data in albums:
        if session.get(Album, album_data["id"]):
            continue
        session.add(Album.model_validate(album_data))


def seed_admin_users(session: Session) -> None:
    for admin in settings.admin_users:
        user = session.exec(select(User).where(User.phone == admin.phone)).first()
        if user is None:
            session.add(User(phone=admin.phone, name=admin.name, password_hash=get_password_hash(admin.password), is_admin=True, upload_approved=True))
            continue
        user.name = admin.name
        user.is_admin = True
        user.upload_approved = True
        session.add(user)


def init_db() -> None:
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    create_db_and_tables()
    with Session(engine) as session:
        seed_albums(session)
        seed_admin_users(session)
        session.commit()
