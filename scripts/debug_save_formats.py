"""Debug different save formats."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print(f"Testing save formats")
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

        # Start session
        response = await client.post(
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
        print(f"Window ID: {window_id}\n")

        # Retrieve item
        await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {"DataWindowName": "d_form", "FieldName": "item_id", "Value": "GBY"}
                ],
            },
        )

        # Test different save formats
        print("Testing save formats:")

        # Format 1: body with WindowId
        print("\n1. PUT body with WindowId...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/data",
            headers=headers,
            json={"WindowId": window_id},
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

        # Format 2: query param
        print("\n2. PUT with query param...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/data",
            headers=headers,
            params={"windowId": window_id},
            json={},
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

        # Format 3: POST instead of PUT
        print("\n3. POST with body...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v2/data",
            headers=headers,
            json={"WindowId": window_id},
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

        # Format 4: In URL
        print("\n4. PUT with windowId in path...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/data/{window_id}",
            headers=headers,
            json={},
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

        # Format 5: body + query
        print("\n5. PUT with both body and query param...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v2/data",
            headers=headers,
            params={"windowId": window_id},
            json={"WindowId": window_id},
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")

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
