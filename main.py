from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from api.main import api_router
from core.config import settings
from core.db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app = FastAPI(openapi_url=f"{settings.API_V1_STR}/openapi.json", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY.get_secret_value(), session_cookie="photo_session", max_age=settings.SESSION_MAX_AGE_SECONDS, same_site="lax", https_only=settings.session_cookie_secure)
if settings.all_cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.all_cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
app.include_router(api_router, prefix=settings.API_V1_STR)
