"""Debug proper item retrieval."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print("Testing proper item retrieval")
    print("=" * 60)

    async with httpx.AsyncClient(verify=False, timeout=60.0, follow_redirects=True) as client:
        # Auth
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

        # Get tools
        print("\n1. Getting tools...")
        response = await client.get(
            f"{ui_server_url}/api/ui/interactive/v2/tools",
            headers=headers,
            params={"windowId": window_id},
        )
        tools = response.json()
        tool_names = [t.get("ToolName") for t in tools]
        print(f"   Tools: {tool_names}")

        # Set item_id with different approaches
        print("\n2. Setting item_id with submit=true (if supported)...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {
                        "DataWindowName": "d_form",
                        "FieldName": "item_id",
                        "Value": "GBY",
                        "Submit": True,  # Try this
                    }
                ],
            },
        )
        result = response.json()
        print(f"   Status: {result.get('Status')}, Events: {result.get('Events')}")

        # Check if item_desc is populated (indicates successful retrieve)
        print("\n3. Checking if data loaded via change on item_desc...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {
                        "DataWindowName": "d_form",
                        "FieldName": "item_desc",
                        "Value": "",  # Try to read current value
                    }
                ],
            },
        )
        result = response.json()
        print(f"   Result: {result}")

        # Try Transaction API GET to retrieve
        print("\n4. Trying Transaction API GET to retrieve item...")
        response = await client.post(
            f"{ui_server_url}/api/v2/transaction/get",
            headers=headers,
            json={
                "Name": "Item",
                "UseCodeValues": False,
                "Transactions": [
                    {
                        "DataElements": [
                            {
                                "Name": "TABPAGE_1.inv_mast",
                                "Type": "Form",
                                "Keys": [],
                                "Rows": [
                                    {
                                        "Edits": [
                                            {"Name": "item_id", "Value": "GBY"}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Summary: {result.get('Summary')}")
            # Look for location data
            transactions = result.get("Results", {}).get("Transactions", [])
            if transactions:
                for elem in transactions[0].get("DataElements", []):
                    name = elem.get("Name", "").lower()
                    if "loc" in name:
                        print(f"   Found: {elem.get('Name')} with {len(elem.get('Rows', []))} rows")
                        if elem.get("Rows"):
                            row = elem["Rows"][0]
                            pg = next((e["Value"] for e in row.get("Edits", []) if e.get("Name") == "product_group_id"), None)
                            print(f"   Row 1 product_group: {pg}")
        else:
            try:
                print(f"   Error: {response.text[:300]}")
            except:
                print(f"   Error response")

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
