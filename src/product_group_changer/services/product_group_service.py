"""Product group management service."""

import logging
from dataclasses import dataclass
from typing import Any

from product_group_changer.integrations.p21.odata import P21OData
from product_group_changer.integrations.p21.client import P21Client

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating an item's product group assertion."""

    valid: bool
    inv_mast_uid: int
    item_id: str | None = None
    expected_product_group_id: str = ""
    actual_product_group_id: str | None = None
    locations: list[dict[str, Any]] | None = None
    error: str | None = None


@dataclass
class ChangeResult:
    """Result of changing product group."""

    success: bool
    inv_mast_uid: int
    item_id: str
    previous_product_group_id: str
    new_product_group_id: str
    locations_changed: list[int]
    error: str | None = None


class ProductGroupService:
    """Service for product group operations.

    Product groups in P21 are stored per-location in inv_loc, not on inv_mast.
    When changing product groups, we need to update ALL inv_loc records for the item.
    """

    def __init__(self, odata: P21OData, client: P21Client | None = None):
        self.odata = odata
        self.client = client

    async def get_item_by_uid(self, inv_mast_uid: int) -> dict[str, Any] | None:
        """Get an inventory item by its UID from inv_mast."""
        results = await self.odata.query(
            table="inv_mast",
            filter_expr=f"inv_mast_uid eq {inv_mast_uid}",
            top=1,
        )
        return results[0] if results else None

    async def get_item_locations(self, inv_mast_uid: int) -> list[dict[str, Any]]:
        """Get all location records for an item from inv_loc."""
        return await self.odata.query(
            table="inv_loc",
            filter_expr=f"inv_mast_uid eq {inv_mast_uid}",
        )

    async def validate_assertion(
        self,
        inv_mast_uid: int,
        expected_product_group_id: str,
    ) -> ValidationResult:
        """Validate that item matches asserted product group at ALL locations.

        Returns ValidationResult with:
        - valid=True and locations if assertion matches
        - valid=False with error details if mismatch or item not found
        """
        # Get master record
        item = await self.get_item_by_uid(inv_mast_uid)
        if item is None:
            return ValidationResult(
                valid=False,
                inv_mast_uid=inv_mast_uid,
                expected_product_group_id=expected_product_group_id,
                error="Item not found",
            )

        item_id = item.get("item_id", "")

        # Get all locations
        locations = await self.get_item_locations(inv_mast_uid)
        if not locations:
            return ValidationResult(
                valid=False,
                inv_mast_uid=inv_mast_uid,
                item_id=item_id,
                expected_product_group_id=expected_product_group_id,
                error="Item has no locations",
            )

        # Check each location - ALL must match
        for loc in locations:
            actual_pg = loc.get("product_group_id", "")
            if actual_pg != expected_product_group_id:
                return ValidationResult(
                    valid=False,
                    inv_mast_uid=inv_mast_uid,
                    item_id=item_id,
                    expected_product_group_id=expected_product_group_id,
                    actual_product_group_id=actual_pg,
                    error=f"Product group mismatch at location {loc.get('location_id')}",
                )

        # All locations match
        return ValidationResult(
            valid=True,
            inv_mast_uid=inv_mast_uid,
            item_id=item_id,
            expected_product_group_id=expected_product_group_id,
            locations=locations,
        )

    async def change_product_group(
        self,
        inv_mast_uid: int,
        item_id: str,
        previous_product_group_id: str,
        desired_product_group_id: str,
        locations: list[dict[str, Any]],
    ) -> ChangeResult:
        """Change product group for item at ALL locations."""
        if not self.client:
            return ChangeResult(
                success=False,
                inv_mast_uid=inv_mast_uid,
                item_id=item_id,
                previous_product_group_id=previous_product_group_id,
                new_product_group_id=desired_product_group_id,
                locations_changed=[],
                error="P21 client not available",
            )

        locations_changed: list[int] = []
        errors: list[str] = []

        for loc in locations:
            location_id = loc.get("location_id")
            try:
                update_result = await self.client.update_inv_loc_product_group(
                    inv_mast_uid=inv_mast_uid,
                    location_id=location_id,
                    new_product_group_id=desired_product_group_id,
                    item_id=item_id,
                )

                if update_result.get("success"):
                    locations_changed.append(location_id)
                else:
                    errors.append(f"Location {location_id}: {update_result.get('message')}")
            except Exception as e:
                logger.error(f"Failed to update location {location_id}: {e}")
                errors.append(f"Location {location_id}: {str(e)}")

        if errors:
            return ChangeResult(
                success=False,
                inv_mast_uid=inv_mast_uid,
                item_id=item_id,
                previous_product_group_id=previous_product_group_id,
                new_product_group_id=desired_product_group_id,
                locations_changed=locations_changed,
                error="; ".join(errors),
            )

        return ChangeResult(
            success=True,
            inv_mast_uid=inv_mast_uid,
            item_id=item_id,
            previous_product_group_id=previous_product_group_id,
            new_product_group_id=desired_product_group_id,
            locations_changed=locations_changed,
        )
