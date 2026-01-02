"""Unit tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from product_group_changer.models.schemas import (
    ChangeProductGroupRequest,
    ItemAssertion,
)


class TestItemAssertion:
    """Tests for ItemAssertion schema."""

    def test_valid_assertion(self) -> None:
        """Test valid item assertion."""
        assertion = ItemAssertion(
            inv_mast_uid=12345,
            expected_product_group_id="FILTERS",
        )
        assert assertion.inv_mast_uid == 12345
        assert assertion.expected_product_group_id == "FILTERS"

    def test_missing_uid_rejected(self) -> None:
        """Test that missing inv_mast_uid is rejected."""
        with pytest.raises(ValidationError):
            ItemAssertion(expected_product_group_id="FILTERS")

    def test_missing_product_group_rejected(self) -> None:
        """Test that missing expected_product_group_id is rejected."""
        with pytest.raises(ValidationError):
            ItemAssertion(inv_mast_uid=12345)


class TestChangeProductGroupRequest:
    """Tests for ChangeProductGroupRequest schema."""

    def test_valid_request(self) -> None:
        """Test valid change request."""
        request = ChangeProductGroupRequest(
            items=[
                ItemAssertion(inv_mast_uid=12345, expected_product_group_id="FILTERS"),
                ItemAssertion(inv_mast_uid=67890, expected_product_group_id="FILTERS"),
            ],
            new_product_group_id="FITTINGS",
        )
        assert len(request.items) == 2
        assert request.new_product_group_id == "FITTINGS"

    def test_empty_items_rejected(self) -> None:
        """Test that empty items list is rejected."""
        with pytest.raises(ValidationError):
            ChangeProductGroupRequest(items=[], new_product_group_id="FITTINGS")

    def test_max_items_limit(self) -> None:
        """Test maximum items limit."""
        # 1000 items should be valid
        items = [
            ItemAssertion(inv_mast_uid=i, expected_product_group_id="FILTERS")
            for i in range(1000)
        ]
        request = ChangeProductGroupRequest(items=items, new_product_group_id="FITTINGS")
        assert len(request.items) == 1000

        # 1001 items should be rejected
        items = [
            ItemAssertion(inv_mast_uid=i, expected_product_group_id="FILTERS")
            for i in range(1001)
        ]
        with pytest.raises(ValidationError):
            ChangeProductGroupRequest(items=items, new_product_group_id="FITTINGS")

    def test_missing_new_product_group_rejected(self) -> None:
        """Test that missing new_product_group_id is rejected."""
        with pytest.raises(ValidationError):
            ChangeProductGroupRequest(
                items=[ItemAssertion(inv_mast_uid=12345, expected_product_group_id="FILTERS")]
            )
