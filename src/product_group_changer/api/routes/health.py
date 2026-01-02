"""Health check endpoints."""

from fastapi import APIRouter, Depends

from product_group_changer.dependencies import AppState, get_app_state
from product_group_changer.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(state: AppState = Depends(get_app_state)) -> HealthResponse:
    """Check application health status."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        p21_connected=state.p21_odata is not None,
    )
