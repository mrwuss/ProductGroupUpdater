"""Debug tools-based save."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print("Testing tools-based save")
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
        window_id = response.json().get("WindowId")
        print(f"Window ID: {window_id}")

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
        print("Retrieved GBY")

        # Get available tools
        print("\nGetting available tools (v2)...")
        response = await client.get(
            f"{ui_server_url}/api/ui/interactive/v2/tools",
            headers=headers,
            params={"windowId": window_id},
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            tools = response.json()
            print(f"Tools: {tools}")

        # Try v1 tools
        print("\nGetting available tools (v1)...")
        response = await client.get(
            f"{ui_server_url}/api/ui/interactive/v1/tools",
            headers=headers,
            params={"windowId": window_id},
        )
        print(f"Status: {response.status_code}")

        # Try to run save tool (v2)
        print("\nTrying to run save tool (v2)...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v2/tools",
            headers=headers,
            json={
                "WindowId": window_id,
                "ToolName": "cb_save",
            },
        )
        print(f"Status: {response.status_code}")
        try:
            print(f"Response: {response.text[:300]}")
        except:
            print(f"Response: {response.content[:300]}")

        # Try different tool name
        print("\nTrying save tool with ToolText...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v2/tools",
            headers=headers,
            json={
                "WindowId": window_id,
                "ToolName": "cb_save",
                "ToolText": "Save",
            },
        )
        print(f"Status: {response.status_code}")

        # Try via v1 tools
        print("\nTrying save tool (v1)...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v1/tools",
            headers=headers,
            json={
                "WindowId": window_id,
                "ToolName": "cb_save",
                "ToolText": "Save",
            },
        )
        print(f"Status: {response.status_code}")

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
