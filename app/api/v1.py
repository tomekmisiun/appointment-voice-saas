from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.files import router as files_router
from app.api.routes.tenants import router as tenants_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes import users


API_V1_PREFIX = "/api/v1"

api_v1_router = APIRouter(prefix=API_V1_PREFIX)

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(files_router)
api_v1_router.include_router(webhooks_router)
