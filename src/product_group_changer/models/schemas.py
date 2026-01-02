"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field


# Health Check
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    p21_connected: bool


# Request schema
class ChangeProductGroupRequest(BaseModel):
    """Request to change product group for a single item."""

    inv_mast_uid: int = Field(..., description="Inventory master UID")
    expected_product_group_id: str = Field(
        ..., description="Expected current product group (for optimistic lock)"
    )
    desired_product_group_id: str = Field(..., description="Desired new product group")


# Response schemas
class SuccessResponse(BaseModel):
    """200 response when update succeeds."""

    inv_mast_uid: int
    item_id: str
    previous_product_group_id: str
    new_product_group_id: str
    locations_changed: list[int]


class ErrorResponse(BaseModel):
    """Error response for 400, 409, 500."""

    error: str
    detail: str | None = None
