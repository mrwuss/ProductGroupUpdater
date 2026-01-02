"""Debug Item window workflow step by step."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print(f"Testing Item window workflow")
    print(f"=" * 60)

    async with httpx.AsyncClient(verify=False, timeout=60.0, follow_redirects=True) as client:
        # Step 1: Authenticate
        print("\n1. Authenticating...")
        response = await client.post(
            f"{BASE_URL}/api/security/token/v2",
            json={"username": USERNAME, "password": PASSWORD},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        token = response.json().get("AccessToken")
        print(f"   Token obtained")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Step 2: Get UI Server URL
        print("\n2. Getting UI Server URL...")
        response = await client.get(
            f"{BASE_URL}/api/ui/router/v1?urlType=external",
            headers=headers,
        )
        response.raise_for_status()
        ui_server_url = response.json().get("Url", "").rstrip("/")
        print(f"   UI Server: {ui_server_url}")

        # Step 3: Start session
        print("\n3. Starting session...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
            json={"ResponseWindowHandlingEnabled": False},
        )
        print(f"   Status: {response.status_code}")
        if response.status_code not in (200, 201):
            print(f"   Response: {response.text[:300]}")
            return

        # Step 4: Open Item window
        print("\n4. Opening Item window...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v2/window",
            headers=headers,
            json={"ServiceName": "Item"},
        )
        print(f"   Status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Response: {response.text[:300]}")
            return

        window_data = response.json()
        window_id = window_data.get("WindowId")
        print(f"   WindowId: {window_id}")

        # Print available datawindows
        print("\n   DataElements:")
        for elem in window_data.get("DataElements", [])[:5]:
            print(f"     - {elem.get('Name')} -> {elem.get('Table')}")
        print("     ...")

        # Step 5: Try to change item_id field
        print("\n5. Changing item_id field to retrieve item 'GBY'...")
        response = await client.put(
            f"{ui_server_url}/api/ui/interactive/v1/change",
            headers=headers,
            json={
                "WindowId": window_id,
                "ChangeRequests": [
                    {
                        "DataWindowName": "d_form",
                        "FieldName": "item_id",
                        "Value": "GBY",
                    }
                ],
            },
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:500]}")

        if response.status_code == 200:
            # Step 6: Try to get window data
            print("\n6. Getting window data...")
            response = await client.get(
                f"{ui_server_url}/api/ui/interactive/v1/data",
                headers=headers,
                params={"windowId": window_id},
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   DataWindows: {[dw.get('Name') for dw in data.get('DataWindows', [])]}")

            # Step 7: Try to change tab
            print("\n7. Changing to TABPAGE_17 (Locations)...")
            response = await client.put(
                f"{ui_server_url}/api/ui/interactive/v1/tab",
                headers=headers,
                json={
                    "WindowId": window_id,
                    "PagePath": {"PageName": "TABPAGE_17"},
                },
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:300]}")

        # Step 8: Close window
        print("\n8. Closing window...")
        response = await client.delete(
            f"{ui_server_url}/api/ui/interactive/v2/window",
            headers=headers,
            params={"windowId": window_id},
        )
        print(f"   Status: {response.status_code}")

        # Step 9: End session
        print("\n9. Ending session...")
        response = await client.delete(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
        )
        print(f"   Status: {response.status_code}")

        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(debug())
