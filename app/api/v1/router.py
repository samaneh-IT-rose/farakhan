"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1 import admin_auth, admin_submissions, files, form_options, locations, submissions

api_router = APIRouter()
api_router.include_router(form_options.router)
api_router.include_router(locations.router)
api_router.include_router(submissions.router)
api_router.include_router(admin_auth.router)
api_router.include_router(admin_submissions.router)
api_router.include_router(files.router)
