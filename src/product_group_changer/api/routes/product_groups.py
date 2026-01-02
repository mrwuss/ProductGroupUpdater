"""Product group change endpoint."""

import logging
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from product_group_changer.dependencies import get_p21_odata, get_p21_client
from product_group_changer.integrations.p21.odata import P21OData
from product_group_changer.integrations.p21.client import P21Client
from product_group_changer.models.schemas import (
    ChangeProductGroupRequest,
    SuccessResponse,
    ErrorResponse,
)
from product_group_changer.services.product_group_service import ProductGroupService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/change-product-group",
    responses={
        200: {"model": SuccessResponse, "description": "Update successful"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        409: {"model": ErrorResponse, "description": "Concurrency conflict"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def change_product_group(
    request: ChangeProductGroupRequest,
    odata: P21OData = Depends(get_p21_odata),
    client: P21Client = Depends(get_p21_client),
) -> JSONResponse:
    """Change product group for an inventory item.

    Response codes:
    - 200: Update successful
    - 400: Bad request (invalid input, item not found)
    - 409: Concurrency conflict (expected product group doesn't match actual)
    - 500: Server error (update failed)
    """
    service = ProductGroupService(odata=odata, client=client)

    try:
        # Validate assertion (optimistic lock check)
        validation = await service.validate_assertion(
            inv_mast_uid=request.inv_mast_uid,
            expected_product_group_id=request.expected_product_group_id,
        )

        if not validation.valid:
            # Determine if 400 (bad request) or 409 (concurrency)
            if validation.actual_product_group_id is not None:
                # Mismatch = concurrency conflict
                return JSONResponse(
                    status_code=409,
                    content=ErrorResponse(
                        error="Concurrency conflict",
                        detail=f"Expected '{request.expected_product_group_id}' but found '{validation.actual_product_group_id}'",
                    ).model_dump(),
                )
            else:
                # Item not found or no locations = bad request
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        error="Bad request",
                        detail=validation.error,
                    ).model_dump(),
                )

        # Execute the change
        result = await service.change_product_group(
            inv_mast_uid=request.inv_mast_uid,
            item_id=validation.item_id or "",
            previous_product_group_id=request.expected_product_group_id,
            desired_product_group_id=request.desired_product_group_id,
            locations=validation.locations or [],
        )

        if not result.success:
            # Update failed = server error
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    error="Update failed",
                    detail=result.error,
                ).model_dump(),
            )

        # Success
        return JSONResponse(
            status_code=200,
            content=SuccessResponse(
                inv_mast_uid=result.inv_mast_uid,
                item_id=result.item_id,
                previous_product_group_id=result.previous_product_group_id,
                new_product_group_id=result.new_product_group_id,
                locations_changed=result.locations_changed,
            ).model_dump(),
        )

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Server error",
                detail=str(e),
            ).model_dump(),
        )
