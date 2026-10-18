from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.users import router as users_router
from app.api.v1.drivers import router as drivers_router
from app.api.v1.clients import router as clients_router
from app.api.v1.assignments import router as assignments_router
from app.api.v1.trips import router as trips_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(companies_router, prefix="/companies", tags=["Companies"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(drivers_router, prefix="/drivers", tags=["Drivers"])
api_router.include_router(clients_router, prefix="/clients", tags=["Clients"])
api_router.include_router(
    assignments_router, prefix="/assignments", tags=["Driver-Client Assignments"]
)
api_router.include_router(trips_router, prefix="/trips", tags=["Trips & Route Optimization"])

