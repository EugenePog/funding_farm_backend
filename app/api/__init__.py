"""API Routes Package"""

from fastapi import APIRouter
from app.api import data, results, health

# Aggregate all routers
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(data.router, prefix="/data", tags=["data"])
api_router.include_router(results.router, prefix="/results", tags=["results"])

__all__ = ["api_router"]