"""Debug full save workflow - try to actually change and save product_group."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print(f"Full save workflow test")
    print(f"=" * 60)

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

        # First, check current value via OData
        print("1. Checking current product_group via OData...")
        odata_response = await client.get(
            f"{BASE_URL}/odataservice/odata/table/inv_loc",
            headers=headers,
            params={"$filter": "inv_mast_uid eq 35923 and location_id eq 10", "$select": "product_group_id,item_id"},
        )
        if odata_response.status_code == 200:
            data = odata_response.json()
            if data.get("value"):
                current_pg = data["value"][0].get("product_group_id")
                print(f"   Current product_group at loc 10: {current_pg}")
        else:
            print(f"   OData error: {odata_response.status_code}")

        # Start Interactive session
        print("\n2. Starting Interactive session...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
            json={"ResponseWindowHandlingEnabled": False},
        )
        print(f"   Status: {response.status_code}")

        # Open Item window
        print("\n3. Opening Item window...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v2/window",
            headers=headers,
            json={"ServiceName": "Item"},
        )
        window_id = response.json().get("WindowId")
        print(f"   Window ID: {window_id}")

        # Retrieve item GBY
        print("\n4. Retrieving item GBY...")
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
        print(f"   Status: {result.get('Status')}, Messages: {result.get('Messages')}")

        # Try changing product_group directly (maybe the field is accessible on main form)
        print("\n5. Trying to change product_group_id on invloclist...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {"DataWindowName": "invloclist", "FieldName": "product_group_id", "Value": "SU5A"}
                ],
            },
        )
        result = response.json()
        print(f"   Status: {result.get('Status')}, Messages: {result.get('Messages')}")

        # Try saving
        print("\n6. Saving...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/data",
            headers=headers,
            json={"WindowId": window_id},
        )
        print(f"   Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Status: {result.get('Status')}, Messages: {result.get('Messages')}")
        else:
            print(f"   Error: {response.text[:300]}")

        # Close window
        print("\n7. Closing window...")
        await client.delete(
            f"{ui_server_url}/api/ui/interactive/v2/window",
            headers=headers,
            params={"windowId": window_id},
        )

        # End session
        await client.delete(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
        )

        # Check if value changed via OData
        print("\n8. Checking product_group via OData again...")
        odata_response = await client.get(
            f"{BASE_URL}/odataservice/odata/table/inv_loc",
            headers=headers,
            params={"$filter": "inv_mast_uid eq 35923 and location_id eq 10", "$select": "product_group_id,item_id"},
        )
        if odata_response.status_code == 200:
            data = odata_response.json()
            if data.get("value"):
                new_pg = data["value"][0].get("product_group_id")
                print(f"   Product_group at loc 10: {new_pg}")
                if new_pg != current_pg:
                    print("   CHANGED!")
                else:
                    print("   NOT changed.")

        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(debug())
