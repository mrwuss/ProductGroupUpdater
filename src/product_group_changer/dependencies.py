"""Dependency injection and application state management."""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Request

from product_group_changer.config import Settings, get_settings

if TYPE_CHECKING:
    from product_group_changer.integrations.p21.client import P21Client
    from product_group_changer.integrations.p21.odata import P21OData

logger = logging.getLogger(__name__)


@dataclass
class AppState:
    """Application state container for dependency injection."""

    settings: Settings
    p21_client: "P21Client | None" = None
    p21_odata: "P21OData | None" = None

    async def initialize(self) -> None:
        """Initialize application resources."""
        from product_group_changer.integrations.p21.client import P21Client
        from product_group_changer.integrations.p21.odata import P21OData

        # Initialize P21 clients
        self.p21_odata = P21OData(
            base_url=self.settings.p21_base_url,
            username=self.settings.p21_username,
            password=self.settings.p21_password,
        )

        self.p21_client = P21Client(
            base_url=self.settings.p21_base_url,
            username=self.settings.p21_username,
            password=self.settings.p21_password,
        )

        logger.info("Application state initialized")

    async def cleanup(self) -> None:
        """Cleanup application resources."""
        if self.p21_odata:
            await self.p21_odata.close()
        if self.p21_client:
            await self.p21_client.close()
        logger.info("Application state cleaned up")


def get_app_state(request: Request) -> AppState:
    """Get application state from request."""
    return request.app.state.app_state


def get_p21_odata(request: Request) -> "P21OData":
    """Get P21 OData client from request."""
    state = get_app_state(request)
    if state.p21_odata is None:
        raise RuntimeError("P21 OData client not initialized")
    return state.p21_odata


def get_p21_client(request: Request) -> "P21Client":
    """Get P21 Interactive client from request."""
    state = get_app_state(request)
    if state.p21_client is None:
        raise RuntimeError("P21 client not initialized")
    return state.p21_client
