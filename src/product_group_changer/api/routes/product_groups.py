"""Product group change endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from product_group_changer.dependencies import get_p21_odata, get_p21_client
from product_group_changer.integrations.p21.odata import P21OData
from product_group_changer.integrations.p21.client import P21Client
from product_group_changer.models.schemas import (
    ChangeProductGroupRequest,
    ChangeResultItem,
    ChangeSuccessResponse,
    ChangePartialFailureResponse,
    MismatchDetail,
    ValidationErrorResponse,
)
from product_group_changer.services.product_group_service import ProductGroupService

router = APIRouter()


@router.post(
    "/change-product-group",
    responses={
        200: {"model": ChangeSuccessResponse, "description": "All changes succeeded"},
        400: {"model": ValidationErrorResponse, "description": "Product group assertion mismatch"},
        403: {"model": ChangePartialFailureResponse, "description": "Some changes failed"},
    },
)
async def change_product_group(
    request: ChangeProductGroupRequest,
    odata: P21OData = Depends(get_p21_odata),
    client: P21Client = Depends(get_p21_client),
) -> JSONResponse:
    """Change product groups for inventory items.

    Workflow:
    1. Validate all items match their asserted current product groups
    2. If any mismatch → return 400 with mismatch details
    3. Update all items to the new product group
    4. If all succeed → return 200 with results
    5. If any fail → return 403 with individual results

    Request body:
    - items: Array of {inv_mast_uid, expected_product_group_id} pairs
    - new_product_group_id: Target product group for all items
    """
    service = ProductGroupService(odata=odata, client=client)

    # Phase 1: Validate assertions
    valid_items, mismatches = await service.validate_assertions(request.items)

    if mismatches:
        # Return 400 - assertions don't match current state
        response = ValidationErrorResponse(
            error="Product group mismatch",
            mismatches=[
                MismatchDetail(
                    inv_mast_uid=m.inv_mast_uid,
                    expected_product_group_id=m.expected_product_group_id,
                    actual_product_group_id=m.actual_product_group_id,
                    item_id=m.item_id,
                    location_id=m.location_id,
                )
                for m in mismatches
            ],
        )
        return JSONResponse(status_code=400, content=response.model_dump())

    # Phase 2: Execute changes
    results = await service.change_product_groups(
        items=valid_items,
    )

    # Convert to response format
    result_items = [
        ChangeResultItem(
            inv_mast_uid=r.inv_mast_uid,
            item_id=r.item_id,
            previous_product_group_id=r.previous_product_group_id,
            new_product_group_id=r.new_product_group_id,
            success=r.success,
            locations_changed=r.locations_changed,
            error=r.error,
        )
        for r in results
    ]

    # Check for failures
    failures = [r for r in results if not r.success]

    if failures:
        # Return 403 - some updates failed
        response = ChangePartialFailureResponse(
            error="Some updates failed",
            total_requested=len(results),
            successful=len(results) - len(failures),
            failed=len(failures),
            results=result_items,
        )
        return JSONResponse(status_code=403, content=response.model_dump())

    # Return 200 - all succeeded
    response = ChangeSuccessResponse(
        total_changed=len(results),
        results=result_items,
    )
    return JSONResponse(status_code=200, content=response.model_dump())
