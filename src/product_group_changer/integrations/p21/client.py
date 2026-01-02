"""P21 Interactive API client for stateful operations.

Reference: ../p21-api-documentation/docs/04-Interactive-API.md

The Interactive API is used for updates because:
- Full business logic validation
- Reliable field-level updates
- Session-based state management
- Can handle response dialogs
"""

import logging
from typing import Any

import httpx

from product_group_changer.core.exceptions import P21AuthError, P21Error

logger = logging.getLogger(__name__)


class P21Client:
    """P21 Interactive API client for stateful CRUD operations.

    Use this client for:
    - Updating existing records
    - Complex workflows with validation
    - Operations that may trigger response dialogs

    For bulk creates, consider Transaction API instead.
    For reads, use P21OData (faster).
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
        self._ui_server_url: str | None = None
        self._client: httpx.AsyncClient | None = None
        self._session_active: bool = False

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
        """Get authentication token."""
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

    async def _get_ui_server_url(self) -> str:
        """Get UI server URL for Interactive/Transaction APIs."""
        if self._ui_server_url:
            return self._ui_server_url

        if not self._token:
            await self._authenticate()

        client = await self._get_client()
        response = await client.get(
            f"{self.base_url}/api/ui/router/v1?urlType=external",
            headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json"},
        )
        response.raise_for_status()
        self._ui_server_url = response.json()["Url"].rstrip("/")
        return self._ui_server_url

    async def _get_headers(self) -> dict[str, str]:
        """Get authorization headers."""
        if not self._token:
            await self._authenticate()

        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def start_session(self) -> None:
        """Start an Interactive API session."""
        if self._session_active:
            return

        ui_url = await self._get_ui_server_url()
        client = await self._get_client()
        headers = await self._get_headers()

        response = await client.post(
            f"{ui_url}/api/ui/interactive/sessions/",
            headers=headers,
            json={"ResponseWindowHandlingEnabled": False},
        )
        response.raise_for_status()
        self._session_active = True
        logger.info("Interactive API session started")

    async def end_session(self) -> None:
        """End the Interactive API session."""
        if not self._session_active:
            return

        try:
            ui_url = await self._get_ui_server_url()
            client = await self._get_client()
            headers = await self._get_headers()

            await client.delete(
                f"{ui_url}/api/ui/interactive/sessions/",
                headers=headers,
            )
            logger.info("Interactive API session ended")
        except Exception as e:
            logger.debug(f"Session cleanup error (ignored): {e}")
        finally:
            self._session_active = False

    async def open_window(self, service_name: str) -> dict[str, Any]:
        """Open a P21 window.

        Args:
            service_name: The service/window name (e.g., 'InventoryMaster')

        Returns:
            Window information including WindowId
        """
        await self.start_session()

        ui_url = await self._get_ui_server_url()
        client = await self._get_client()
        headers = await self._get_headers()

        response = await client.post(
            f"{ui_url}/api/ui/interactive/v2/window",
            headers=headers,
            json={"ServiceName": service_name},
        )
        response.raise_for_status()
        return response.json()

    async def close_window(self, window_id: str) -> None:
        """Close a P21 window."""
        ui_url = await self._get_ui_server_url()
        client = await self._get_client()
        headers = await self._get_headers()

        await client.delete(
            f"{ui_url}/api/ui/interactive/v2/window",
            headers=headers,
            params={"windowId": window_id},
        )

    async def change_data(
        self,
        window_id: str,
        tab_name: str,
        field_name: str,
        value: str,
        datawindow_name: str | None = None,
    ) -> dict[str, Any]:
        """Change a field value in the window.

        Based on working Cube Writer implementation - uses TabName and List format.

        Args:
            window_id: The window ID from open_window
            tab_name: The tab containing the field (e.g., 'FORM', 'TABPAGE_1')
            field_name: The field name to change
            value: The new value
            datawindow_name: Optional datawindow name if ambiguous

        Returns:
            API response
        """
        ui_url = await self._get_ui_server_url()
        client = await self._get_client()
        headers = await self._get_headers()

        change_request = {
            "TabName": tab_name,
            "FieldName": field_name,
            "Value": str(value) if value is not None else "",
        }
        if datawindow_name:
            change_request["DatawindowName"] = datawindow_name

        response = await client.put(
            f"{ui_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "List": [change_request],
            },
        )
        response.raise_for_status()
        return response.json()

    async def save_data(self, window_id: str) -> dict[str, Any]:
        """Save changes in the window.

        Based on working Cube Writer implementation - sends just the window_id GUID.
        """
        ui_url = await self._get_ui_server_url()
        client = await self._get_client()
        headers = await self._get_headers()

        # Note: Per Cube Writer, just send the window_id as the JSON body (not wrapped in object)
        response = await client.put(
            f"{ui_url}/api/ui/interactive/v2/data",
            headers=headers,
            json=window_id,  # Just the GUID string, not {"WindowId": ...}
        )
        response.raise_for_status()
        return response.json()

    async def change_tab(self, window_id: str, tab_name: str) -> dict[str, Any]:
        """Change the active tab in a window.

        Based on working Cube Writer implementation - uses PageName directly.

        Args:
            window_id: The window ID
            tab_name: The tab name (e.g., 'TABPAGE_17')

        Returns:
            API response
        """
        ui_url = await self._get_ui_server_url()
        client = await self._get_client()
        headers = await self._get_headers()

        response = await client.put(
            f"{ui_url}/api/ui/interactive/v2/tab",
            headers=headers,
            json={
                "WindowId": window_id,
                "PageName": tab_name,  # Direct PageName, not PagePath wrapper
            },
        )
        response.raise_for_status()
        return response.json()

    async def change_row(
        self,
        window_id: str,
        datawindow_name: str,
        row: int,
    ) -> dict[str, Any]:
        """Change the current row in a datawindow.

        Based on working Cube Writer implementation - uses Row and DatawindowName.

        Args:
            window_id: The window ID
            datawindow_name: The datawindow name
            row: The row index (0-based per Cube Writer)

        Returns:
            API response
        """
        ui_url = await self._get_ui_server_url()
        client = await self._get_client()
        headers = await self._get_headers()

        response = await client.put(
            f"{ui_url}/api/ui/interactive/v2/row",
            headers=headers,
            json={
                "WindowId": window_id,
                "DatawindowName": datawindow_name,  # Note: lowercase 'w'
                "Row": row,  # Row, not RowNumber
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_window_data(self, window_id: str) -> dict[str, Any]:
        """Get current data from a window.

        Based on working Cube Writer implementation - uses id query param.

        Args:
            window_id: The window ID

        Returns:
            Window data including all datawindows
        """
        ui_url = await self._get_ui_server_url()
        client = await self._get_client()
        headers = await self._get_headers()

        response = await client.get(
            f"{ui_url}/api/ui/interactive/v2/data?id={window_id}",
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    async def update_inv_loc_product_group(
        self,
        inv_mast_uid: int,
        location_id: int,
        new_product_group_id: str,
        item_id: str | None = None,
    ) -> dict[str, Any]:
        """Update product group for an item at a specific location.

        Product groups are stored in inv_loc (per location), not inv_mast.
        Uses the Item window to make changes via the Location Detail tab.

        Workflow:
        1. Open Item window
        2. Retrieve item by item_id (TABPAGE_1)
        3. Navigate to Locations tab (TABPAGE_17)
        4. Find and select the correct location row in invloclist
        5. Navigate to Location Detail tab (TABPAGE_18)
        6. Verify correct location is showing in inv_loc_detail
        7. Change product_group_id
        8. Save

        Note: Row selection uses _internalrowindex (1-based), not array index.

        Args:
            inv_mast_uid: The inventory master UID
            location_id: The location ID
            new_product_group_id: The new product group ID
            item_id: Optional item_id (if already known, skips lookup)

        Returns:
            Result dictionary with success status and message
        """
        # Get item_id if not provided
        if not item_id:
            if not self._token:
                await self._authenticate()

            client = await self._get_client()
            headers = await self._get_headers()

            odata_url = f"{self.base_url}/odataservice/odata/table/inv_mast"
            odata_headers = {**headers, "Accept": "application/json"}
            resp = await client.get(
                odata_url,
                params={"$filter": f"inv_mast_uid eq {inv_mast_uid}"},
                headers=odata_headers,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("value"):
                return {"success": False, "message": f"Item not found: {inv_mast_uid}"}

            item_id = data["value"][0]["item_id"]

        # Open Item window
        window_info = await self.open_window("Item")
        window_id = window_info["WindowId"]
        logger.info(f"Opened Item window: {window_id}")

        try:
            # Step 1: Retrieve the item by item_id on TABPAGE_1 (main tab)
            logger.info(f"Retrieving item {item_id}")
            retrieve_result = await self.change_data(
                window_id,
                tab_name="TABPAGE_1",
                field_name="item_id",
                value=item_id,
            )
            logger.debug(f"Retrieve result: {retrieve_result}")

            # Step 2: Navigate to Locations tab (TABPAGE_17)
            await self.change_tab(window_id, "TABPAGE_17")

            # Step 3: Get window data to find the row for this location
            window_data = await self.get_window_data(window_id)

            internal_row_idx = None
            total_rows = 0
            for dw in window_data:
                dw_name = dw.get("Name", "")
                if "invloclist" in dw_name.lower():
                    cols = dw.get("Columns", [])
                    rows = dw.get("Data", [])
                    total_rows = len(rows)
                    if "location_id" in cols and "_internalrowindex" in cols:
                        loc_col_idx = cols.index("location_id")
                        internal_idx_col = cols.index("_internalrowindex")
                        for i, row in enumerate(rows):
                            if str(row[loc_col_idx]) == str(location_id):
                                internal_row_idx = row[internal_idx_col]
                                break
                    break

            if internal_row_idx is None:
                return {
                    "success": False,
                    "message": f"Location {location_id} not found for item {item_id}",
                }

            logger.info(f"Found location {location_id} at internal row {internal_row_idx} of {total_rows}")

            # Step 4: Select the target row (uses _internalrowindex, 1-based)
            await self.change_row(window_id, "invloclist", internal_row_idx)

            # Step 5: Navigate to Location Detail tab (TABPAGE_18)
            await self.change_tab(window_id, "TABPAGE_18")

            # Step 6: Verify correct location is showing
            window_data = await self.get_window_data(window_id)
            detail_location = None
            for dw in window_data:
                dw_name = dw.get("Name", "")
                if "inv_loc_detail" in dw_name.lower():
                    cols = dw.get("Columns", [])
                    rows = dw.get("Data", [])
                    if rows and "location_id" in cols:
                        detail_location = rows[0][cols.index("location_id")]
                    break

            if str(detail_location) != str(location_id):
                return {
                    "success": False,
                    "message": f"Detail view shows location {detail_location}, expected {location_id}",
                }

            # Step 7: Change product_group_id on the detail tab
            logger.info(f"Changing product_group_id to {new_product_group_id} at location {location_id}")
            change_result = await self.change_data(
                window_id,
                tab_name="TABPAGE_18",
                field_name="product_group_id",
                value=new_product_group_id,
                datawindow_name="inv_loc_detail",
            )
            logger.debug(f"Change result: {change_result}")

            if change_result.get("Status") != 1:
                return {
                    "success": False,
                    "message": f"Change failed: {change_result.get('Messages', [])}",
                    "result": change_result,
                }

            # Step 8: Save
            logger.info("Saving changes")
            result = await self.save_data(window_id)
            logger.debug(f"Save result: {result}")

            status = result.get("Status", 0)
            messages = result.get("Messages", [])

            if status == 2:
                if messages:
                    return {
                        "success": False,
                        "message": f"Save issue: {messages}",
                        "result": result,
                    }
                logger.warning(f"Save returned status 2 with no messages for {item_id}")

            return {
                "success": True,
                "message": f"Updated {item_id} at location {location_id} to {new_product_group_id}",
                "result": result,
            }

        except P21Error as e:
            return {
                "success": False,
                "message": str(e),
            }
        except Exception as e:
            logger.error(f"Error updating {item_id} at {location_id}: {e}")
            return {
                "success": False,
                "message": str(e),
            }
        finally:
            await self.close_window(window_id)

    async def close(self) -> None:
        """Close the client and end any active session."""
        await self.end_session()
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "P21Client":
        """Async context manager entry."""
        await self._authenticate()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Async context manager exit."""
        await self.close()
        return False
