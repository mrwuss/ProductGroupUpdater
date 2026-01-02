"""Debug Item window workflow - find how to change product_group_id."""

import asyncio
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print(f"Debugging Item window workflow")
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
        print(f"UI Server: {ui_server_url}\n")

        # Start session
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
            json={"ResponseWindowHandlingEnabled": False},
        )
        print(f"Session: {response.status_code}")

        # Open window
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v2/window",
            headers=headers,
            json={"ServiceName": "Item"},
        )
        print(f"Open Window: {response.status_code}")
        window_data = response.json()
        window_id = window_data.get("WindowId")
        print(f"Window ID: {window_id}")

        # Show all data elements
        print(f"\nDataElements that have 'product' in name or contain 'loc':")
        for elem in window_data.get("DataElements", []):
            name = elem.get("Name", "").lower()
            if "product" in name or "loc" in name:
                print(f"  - {elem.get('Name')} -> {elem.get('Table')}")

        # Retrieve item GBY
        print("\n1. Retrieving item GBY...")
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
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Response: {response.text[:300]}")

        # Get window state after retrieving
        print("\n2. Getting window state...")
        response = await client.get(
            f"{ui_server_url}/api/ui/interactive/v2/window",
            headers=headers,
            params={"windowId": window_id},
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            state = response.json()
            # Look for location-related datawindows
            for dw in state.get("DataWindows", []):
                name = dw.get("Name", "").lower()
                if "loc" in name or "inv" in name:
                    rows = dw.get("Rows", [])
                    print(f"\n   DataWindow: {dw.get('Name')} ({len(rows)} rows)")
                    if rows:
                        print(f"   Fields: {list(rows[0].keys())[:10]}...")
                        for idx, row in enumerate(rows[:2]):
                            location_id = row.get("location_id")
                            product_group_id = row.get("product_group_id")
                            print(f"   Row {idx+1}: location={location_id}, product_group={product_group_id}")

        # Try direct change without tab navigation
        print("\n3. Trying to change product_group_id directly on invloclist...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {"DataWindowName": "invloclist", "FieldName": "product_group_id", "Value": "SU5B"}
                ],
            },
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:300]}")

        # Try on inv_loc_detail
        print("\n4. Trying to change on inv_loc_detail...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {"DataWindowName": "inv_loc_detail", "FieldName": "product_group_id", "Value": "SU5B"}
                ],
            },
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:300]}")

        # Try different row selection method
        print("\n5. Trying row change endpoint...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/row",
            headers=headers,
            json={
                "WindowId": window_id,
                "DataWindowName": "invloclist",
                "RowNumber": 1,
            },
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:300]}")

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

        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(debug())
