"""Product group management service."""

import logging
from dataclasses import dataclass
from typing import Any

from product_group_changer.integrations.p21.odata import P21OData
from product_group_changer.integrations.p21.client import P21Client
from product_group_changer.models.schemas import ItemChange

logger = logging.getLogger(__name__)


@dataclass
class MismatchInfo:
    """Information about a product group mismatch."""

    inv_mast_uid: int
    expected_product_group_id: str
    actual_product_group_id: str
    item_id: str | None = None
    location_id: int | None = None


@dataclass
class ChangeResult:
    """Result of a single item change."""

    inv_mast_uid: int
    item_id: str
    previous_product_group_id: str
    new_product_group_id: str
    success: bool
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
        """Get all location records for an item from inv_loc.

        Product group is stored at the location level, not master level.
        """
        return await self.odata.query(
            table="inv_loc",
            filter_expr=f"inv_mast_uid eq {inv_mast_uid}",
        )

    async def validate_assertions(
        self,
        items: list[ItemChange],
    ) -> tuple[list[dict[str, Any]], list[MismatchInfo]]:
        """Validate that all items match their asserted product groups.

        Checks ALL locations for each item - all must have the expected product group.

        Args:
            items: List of item assertions to validate

        Returns:
            Tuple of (valid_items, mismatches)
        """
        valid_items: list[dict[str, Any]] = []
        mismatches: list[MismatchInfo] = []

        for item_change in items:
            # Get master record for item_id
            item = await self.get_item_by_uid(item_change.inv_mast_uid)

            if item is None:
                mismatches.append(
                    MismatchInfo(
                        inv_mast_uid=item_change.inv_mast_uid,
                        expected_product_group_id=item_change.expected_product_group_id,
                        actual_product_group_id="ITEM_NOT_FOUND",
                        item_id=None,
                    )
                )
                continue

            # Get all locations for this item
            locations = await self.get_item_locations(item_change.inv_mast_uid)

            if not locations:
                mismatches.append(
                    MismatchInfo(
                        inv_mast_uid=item_change.inv_mast_uid,
                        expected_product_group_id=item_change.expected_product_group_id,
                        actual_product_group_id="NO_LOCATIONS",
                        item_id=item.get("item_id"),
                    )
                )
                continue

            # Check each location - ALL must match the expected product group
            location_mismatches = []
            for loc in locations:
                actual_pg = loc.get("product_group_id", "")
                if actual_pg != item_change.expected_product_group_id:
                    location_mismatches.append(
                        MismatchInfo(
                            inv_mast_uid=item_change.inv_mast_uid,
                            expected_product_group_id=item_change.expected_product_group_id,
                            actual_product_group_id=actual_pg,
                            item_id=item.get("item_id"),
                            location_id=loc.get("location_id"),
                        )
                    )

            if location_mismatches:
                mismatches.extend(location_mismatches)
            else:
                # All locations match - add to valid items
                valid_items.append({
                    "inv_mast_uid": item_change.inv_mast_uid,
                    "item_id": item.get("item_id"),
                    "item_desc": item.get("item_desc"),
                    "expected_product_group_id": item_change.expected_product_group_id,
                    "desired_product_group_id": item_change.desired_product_group_id,
                    "locations": locations,
                })

        return valid_items, mismatches

    async def change_product_groups(
        self,
        items: list[dict[str, Any]],
    ) -> list[ChangeResult]:
        """Change product groups for validated items at ALL locations.

        Each item has its own desired_product_group_id.
        """
        results: list[ChangeResult] = []

        for item in items:
            inv_mast_uid = item["inv_mast_uid"]
            item_id = item.get("item_id", "")
            previous_group = item.get("expected_product_group_id", "")
            desired_group = item.get("desired_product_group_id", "")
            locations = item.get("locations", [])

            try:
                if self.client:
                    # Update each location using Interactive API
                    locations_changed: list[int] = []
                    errors: list[str] = []

                    for loc in locations:
                        location_id = loc.get("location_id")
                        update_result = await self.client.update_inv_loc_product_group(
                            inv_mast_uid=inv_mast_uid,
                            location_id=location_id,
                            new_product_group_id=desired_group,
                            item_id=item_id,  # Pass item_id to avoid redundant lookup
                        )

                        if update_result.get("success"):
                            locations_changed.append(location_id)
                        else:
                            errors.append(f"Location {location_id}: {update_result.get('message')}")

                    if errors:
                        results.append(
                            ChangeResult(
                                inv_mast_uid=inv_mast_uid,
                                item_id=item_id,
                                previous_product_group_id=previous_group,
                                new_product_group_id=desired_group,
                                success=False,
                                locations_changed=locations_changed,
                                error="; ".join(errors),
                            )
                        )
                    else:
                        results.append(
                            ChangeResult(
                                inv_mast_uid=inv_mast_uid,
                                item_id=item_id,
                                previous_product_group_id=previous_group,
                                new_product_group_id=desired_group,
                                success=True,
                                locations_changed=locations_changed,
                            )
                        )
                else:
                    results.append(
                        ChangeResult(
                            inv_mast_uid=inv_mast_uid,
                            item_id=item_id,
                            previous_product_group_id=previous_group,
                            new_product_group_id=desired_group,
                            success=False,
                            locations_changed=[],
                            error="P21 client not available",
                        )
                    )

            except Exception as e:
                logger.error(f"Failed to update {item_id}: {e}")
                results.append(
                    ChangeResult(
                        inv_mast_uid=inv_mast_uid,
                        item_id=item_id,
                        previous_product_group_id=previous_group,
                        new_product_group_id=desired_group,
                        success=False,
                        locations_changed=[],
                        error=str(e),
                    )
                )

        return results
