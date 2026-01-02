"""Debug row-specific change in Item window."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print("Testing row-specific changes")
    print("=" * 60)

    async with httpx.AsyncClient(verify=False, timeout=60.0, follow_redirects=True) as client:
        # Authenticate
        response = await client.post(
            f"{BASE_URL}/api/security/token/v2",
            json={"username": USERNAME, "password": PASSWORD},
            headers={"Accept": "application/json"},
        )
        token = response.json().get("AccessToken")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Get UI Server
        response = await client.get(
            f"{BASE_URL}/api/ui/router/v1?urlType=external",
            headers=headers,
        )
        ui_server_url = response.json().get("Url", "").rstrip("/")

        # Start session
        await client.post(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
            json={"ResponseWindowHandlingEnabled": False},
        )

        # Open window
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v2/window",
            headers=headers,
            json={"ServiceName": "Item"},
        )
        window_id = response.json().get("WindowId")
        print(f"Window ID: {window_id}")

        # Retrieve item
        print("\n1. Retrieving GBY...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {"DataWindowName": "d_form", "FieldName": "item_id", "Value": "GBY"}
                ],
            },
        )
        result = response.json()
        print(f"   Status: {result.get('Status')}")

        # Try change with Row parameter
        print("\n2. Trying change with Row parameter...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {
                        "DataWindowName": "invloclist",
                        "FieldName": "product_group_id",
                        "Value": "SU5A",
                        "Row": 1,  # Try specifying row
                    }
                ],
            },
        )
        result = response.json()
        print(f"   Status: {result.get('Status')}, Messages: {result.get('Messages')}")

        # Try with RowNumber instead
        print("\n3. Trying change with RowNumber parameter...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {
                        "DataWindowName": "invloclist",
                        "FieldName": "product_group_id",
                        "Value": "SU5A",
                        "RowNumber": 1,
                    }
                ],
            },
        )
        result = response.json()
        print(f"   Status: {result.get('Status')}, Messages: {result.get('Messages')}")

        # Try selecting row first via row endpoint
        print("\n4. Selecting row 1 first...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/row",
            headers=headers,
            json={
                "WindowId": window_id,
                "DataWindowName": "invloclist",
                "RowNumber": 1,
            },
        )
        result = response.json()
        print(f"   Status: {result.get('Status')}, Messages: {result.get('Messages')}")

        # Now try change
        print("\n5. Changing after row select...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {
                        "DataWindowName": "invloclist",
                        "FieldName": "product_group_id",
                        "Value": "SU5A",
                    }
                ],
            },
        )
        result = response.json()
        print(f"   Status: {result.get('Status')}, Messages: {result.get('Messages')}")

        # Try on inv_loc_detail
        print("\n6. Trying on inv_loc_detail after row select...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {
                        "DataWindowName": "inv_loc_detail",
                        "FieldName": "product_group_id",
                        "Value": "SU5A",
                    }
                ],
            },
        )
        result = response.json()
        print(f"   Status: {result.get('Status')}, Messages: {result.get('Messages')}")

        # Save
        print("\n7. Saving with Quick.Save...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v2/tools",
            headers=headers,
            json={
                "WindowId": window_id,
                "ToolName": "Quick.Save",
            },
        )
        result = response.json()
        print(f"   Status: {result.get('Status')}, Messages: {result.get('Messages')}")

        # Cleanup
        await client.delete(
            f"{ui_server_url}/api/ui/interactive/v2/window",
            headers=headers,
            params={"windowId": window_id},
        )
        await client.delete(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
        )

        # Verify via OData
        print("\n8. Verifying via OData...")
        response = await client.get(
            f"{BASE_URL}/odataservice/odata/table/inv_loc",
            headers=headers,
            params={
                "$filter": "inv_mast_uid eq 35923 and location_id eq 10",
                "$select": "product_group_id",
            },
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("value"):
                pg = data["value"][0].get("product_group_id")
                print(f"   product_group at loc 10: {pg}")

        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(debug())
