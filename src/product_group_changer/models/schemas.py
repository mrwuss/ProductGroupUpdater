"""Pydantic schemas for API request/response validation."""

from pydantic import BaseModel, Field


# Health Check
class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    p21_connected: bool


# Request schemas
class ItemChange(BaseModel):
    """An item with its expected current and desired new product group."""

    inv_mast_uid: int = Field(..., description="Inventory master UID")
    expected_product_group_id: str = Field(..., description="Expected current product group (for validation)")
    desired_product_group_id: str = Field(..., description="Desired new product group")


class ChangeProductGroupRequest(BaseModel):
    """Request to change product groups for multiple items."""

    items: list[ItemChange] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Items with their expected and desired product groups",
    )


# Response schemas
class MismatchDetail(BaseModel):
    """Details of a product group mismatch."""

    inv_mast_uid: int
    expected_product_group_id: str
    actual_product_group_id: str
    item_id: str | None = None
    location_id: int | None = None


class ValidationErrorResponse(BaseModel):
    """400 response when assertions don't match current state."""

    error: str = "Product group mismatch"
    mismatches: list[MismatchDetail]


class ChangeResultItem(BaseModel):
    """Result of a single item's product group change."""

    inv_mast_uid: int
    item_id: str
    previous_product_group_id: str
    new_product_group_id: str
    success: bool
    locations_changed: list[int] = []
    error: str | None = None


class ChangeSuccessResponse(BaseModel):
    """200 response when all changes succeed."""

    total_changed: int
    results: list[ChangeResultItem]


class ChangePartialFailureResponse(BaseModel):
    """403 response when some changes failed."""

    error: str = "Some updates failed"
    total_requested: int
    successful: int
    failed: int
    results: list[ChangeResultItem]
