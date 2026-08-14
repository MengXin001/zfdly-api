from fastapi import APIRouter

from api.routes import albums, auth, photos, utils

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(albums.router)
api_router.include_router(photos.router)
api_router.include_router(utils.router)
