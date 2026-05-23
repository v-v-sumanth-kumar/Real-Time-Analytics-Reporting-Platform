from fastapi import APIRouter

from app.api.v1 import alerts, api_keys, auth, dashboards, events, health, notifications, organizations

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(api_keys.router)
api_router.include_router(events.router)
api_router.include_router(dashboards.router)
api_router.include_router(alerts.router)
api_router.include_router(notifications.router)
