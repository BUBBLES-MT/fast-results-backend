# backend/app/api/v1/academic/__init__.py
from fastapi import APIRouter
from app.api.v1.academic.unassigned import router as unassigned_router

# Create main router for academic module
router = APIRouter()

# Include all sub-routers
router.include_router(unassigned_router, tags=["Academic Unassigned"])