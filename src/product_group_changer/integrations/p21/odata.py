"""P21 OData API client for read operations.

Reference: ../p21-api-documentation/docs/02-OData-API.md
"""

import logging
from datetime import date, timedelta
from typing import Any

import httpx

from product_group_changer.core.exceptions import P21AuthError, P21Error

logger = logging.getLogger(__name__)


class P21OData:
    """P21 OData API client for read-only data access.

    The OData API is the fastest way to query P21 data:
    - Read-only operations
    - Standard OData v4 protocol
    - Supports $filter, $select, $orderby, $top, $skip
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self._token: str | None = None
        self._client: httpx.AsyncClient | None = None

    @property
    def odata_url(self) -> str:
        """Get the OData service base URL."""
        return f"{self.base_url}/odataservice/odata"

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                verify=self.verify_ssl,
                timeout=60.0,
                follow_redirects=True,
            )
        return self._client

    async def _authenticate(self) -> str:
        """Get authentication token.

        Uses V2 token endpoint (recommended).
        Reference: ../p21-api-documentation/docs/00-Authentication.md
        """
        client = await self._get_client()

        response = await client.post(
            f"{self.base_url}/api/security/token/v2",
            json={"username": self.username, "password": self.password},
            headers={"Accept": "application/json"},
        )

        if response.status_code == 401:
            raise P21AuthError("Invalid P21 credentials")

        response.raise_for_status()
        data = response.json()
        self._token = data["AccessToken"]
        return self._token

    async def _get_headers(self) -> dict[str, str]:
        """Get authorization headers, refreshing token if needed."""
        if not self._token:
            await self._authenticate()

        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
        }

    async def query(
        self,
        table: str,
        filter_expr: str | None = None,
        select: list[str] | None = None,
        orderby: str | None = None,
        top: int | None = None,
        skip: int | None = None,
    ) -> list[dict[str, Any]]:
        """Execute OData query against a table.

        Args:
            table: Table name (e.g., 'product_group', 'inv_mast')
            filter_expr: OData $filter expression
            select: Fields to return
            orderby: Sort expression
            top: Limit results
            skip: Skip records (for pagination)

        Returns:
            List of records as dictionaries
        """
        client = await self._get_client()
        headers = await self._get_headers()

        params: dict[str, Any] = {}
        if filter_expr:
            params["$filter"] = filter_expr
        if select:
            params["$select"] = ",".join(select)
        if orderby:
            params["$orderby"] = orderby
        if top:
            params["$top"] = top
        if skip:
            params["$skip"] = skip

        url = f"{self.odata_url}/table/{table}"

        try:
            response = await client.get(url, params=params, headers=headers)

            # Handle token expiration
            if response.status_code == 401:
                await self._authenticate()
                headers = await self._get_headers()
                response = await client.get(url, params=params, headers=headers)

            response.raise_for_status()
            data = response.json()
            return data.get("value", [])

        except httpx.HTTPStatusError as e:
            logger.error(f"OData query failed: {e.response.text}")
            raise P21Error(f"OData query failed: {e.response.status_code}")

    async def get_product_groups(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Get all product groups.

        Args:
            active_only: Only return active records (row_status_flag = 704)
        """
        filter_expr = "row_status_flag eq 704" if active_only else None

        return await self.query(
            table="product_group",
            filter_expr=filter_expr,
            select=["product_group_id", "description", "row_status_flag"],
            orderby="product_group_id",
        )

    async def get_product_group(self, product_group_id: str) -> dict[str, Any] | None:
        """Get a single product group by ID."""
        results = await self.query(
            table="product_group",
            filter_expr=f"product_group_id eq '{product_group_id}'",
            top=1,
        )
        return results[0] if results else None

    async def get_items(
        self,
        product_group_id: str | None = None,
        item_id_contains: str | None = None,
        description_contains: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search inventory items.

        Args:
            product_group_id: Filter by exact product group ID
            item_id_contains: Filter by item ID containing this string
            description_contains: Filter by description containing this string
            limit: Maximum results to return
        """
        filters: list[str] = ["row_status_flag eq 704"]

        if product_group_id:
            filters.append(f"product_group_id eq '{product_group_id}'")
        if item_id_contains:
            filters.append(f"contains(item_id,'{item_id_contains}')")
        if description_contains:
            filters.append(f"contains(item_desc,'{description_contains}')")

        filter_expr = " and ".join(filters)

        return await self.query(
            table="inv_mast",
            filter_expr=filter_expr,
            select=[
                "item_id",
                "item_desc",
                "product_group_id",
                "supplier_id",
            ],
            orderby="item_id",
            top=limit,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
