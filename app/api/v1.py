from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.availability import router as availability_router
from app.api.routes.availability_exceptions import router as availability_exceptions_router
from app.api.routes.bookings import router as bookings_router
from app.api.routes.businesses import router as businesses_router
from app.api.routes.files import router as files_router
from app.api.routes.services import router as services_router
from app.api.routes.staff import router as staff_router
from app.api.routes.tenants import router as tenants_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.working_hours import router as working_hours_router
from app.api.routes import users


API_V1_PREFIX = "/api/v1"

api_v1_router = APIRouter(prefix=API_V1_PREFIX)

api_v1_router.include_router(auth_router)
api_v1_router.include_router(users.router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(files_router)
api_v1_router.include_router(webhooks_router)
api_v1_router.include_router(businesses_router)
api_v1_router.include_router(staff_router)
api_v1_router.include_router(services_router)
api_v1_router.include_router(working_hours_router)
api_v1_router.include_router(availability_exceptions_router)
api_v1_router.include_router(availability_router)
api_v1_router.include_router(bookings_router)
