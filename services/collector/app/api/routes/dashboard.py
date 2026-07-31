from fastapi import APIRouter

from app.services.dashboard_service import dashboard_service

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
)


@router.get("")
async def get_dashboard():
    return await dashboard_service.get_dashboard()
