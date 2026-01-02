"""Pytest configuration and fixtures."""

import pytest
from unittest.mock import AsyncMock

from product_group_changer.config import Settings
from product_group_changer.integrations.p21.odata import P21OData
from product_group_changer.integrations.p21.client import P21Client


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        p21_base_url="https://test.p21.local",
        p21_username="test_user",
        p21_password="test_pass",
        app_env="test",
        debug=True,
    )


@pytest.fixture
def mock_odata() -> AsyncMock:
    """Create mock P21 OData client."""
    mock = AsyncMock(spec=P21OData)

    # Default: return items that match assertions
    mock.query.return_value = [
        {
            "inv_mast_uid": 12345,
            "item_id": "FILT-001",
            "item_desc": "Oil Filter",
            "product_group_id": "FILTERS",
        },
    ]

    return mock


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create mock P21 Interactive client."""
    mock = AsyncMock(spec=P21Client)

    # Default: successful update
    mock.update_item_product_group.return_value = {
        "success": True,
        "message": "Updated successfully",
    }

    return mock


@pytest.fixture
def sample_items() -> list[dict]:
    """Sample inventory item data."""
    return [
        {
            "inv_mast_uid": 12345,
            "item_id": "FILT-001",
            "item_desc": "Oil Filter 10 Micron",
            "product_group_id": "FILTERS",
        },
        {
            "inv_mast_uid": 67890,
            "item_id": "FILT-002",
            "item_desc": "Air Filter 5 Micron",
            "product_group_id": "FILTERS",
        },
    ]
