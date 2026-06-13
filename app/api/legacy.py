from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.files import router as files_router
from app.api.routes.tenants import router as tenants_router
from app.api.routes import users


legacy_api_router = APIRouter(deprecated=True)

legacy_api_router.include_router(auth_router)
legacy_api_router.include_router(users.router)
legacy_api_router.include_router(admin_router)
legacy_api_router.include_router(tenants_router)
legacy_api_router.include_router(files_router)
