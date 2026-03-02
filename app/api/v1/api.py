from fastapi import APIRouter

from app.api.v1.routes.documents import router as documents_router
from app.api.v1.routes.query import router as query_router

api_router = APIRouter()
api_router.include_router(documents_router)
api_router.include_router(query_router)
