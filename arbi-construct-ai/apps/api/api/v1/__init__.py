from fastapi import APIRouter

from api.v1.routers import ai, auth, cases, claims, documents, institutions, procedure, search, timeline

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(documents.router)
api_router.include_router(timeline.router)
api_router.include_router(claims.router)
api_router.include_router(procedure.router)
api_router.include_router(institutions.router)
api_router.include_router(ai.router)
api_router.include_router(search.router)
