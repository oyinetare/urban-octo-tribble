from fastapi import APIRouter

from app.api.v1.routes import auth, documents, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
