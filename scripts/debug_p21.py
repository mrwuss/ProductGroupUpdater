"""Debug P21 Interactive API connection step by step."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print(f"BASE_URL: {BASE_URL}")
    print(f"USERNAME: {USERNAME}")
    print(f"PASSWORD: {'*' * len(PASSWORD) if PASSWORD else 'NOT SET'}")
    print()

    async with httpx.AsyncClient(verify=False, timeout=60.0, follow_redirects=True) as client:
        # Step 1: Authenticate
        print("Step 1: Authenticating...")
        response = await client.post(
            f"{BASE_URL}/api/security/token/v2",
            json={"username": USERNAME, "password": PASSWORD},
            headers={"Accept": "application/json"},
        )
        print(f"  Status: {response.status_code}")
        if response.status_code != 200:
            print(f"  Response: {response.text[:500]}")
            return

        token_data = response.json()
        token = token_data.get("AccessToken")
        print(f"  Token: {token[:50]}..." if token else "  No token!")
        print()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Step 2: Get UI Server URL
        print("Step 2: Getting UI Server URL...")
        response = await client.get(
            f"{BASE_URL}/api/ui/router/v1?urlType=external",
            headers=headers,
        )
        print(f"  Status: {response.status_code}")
        if response.status_code != 200:
            print(f"  Response: {response.text[:500]}")
            return

        ui_data = response.json()
        ui_server_url = ui_data.get("Url", "").rstrip("/")
        print(f"  UI Server: {ui_server_url}")
        print()

        # Step 3: Start session
        print("Step 3: Starting Interactive session...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
            json={"ResponseWindowHandlingEnabled": False},
        )
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text[:500]}")
        if response.status_code not in (200, 201):
            return
        print()

        # Step 4: Try opening different windows
        service_names = ["SalesPricePage", "Customer", "Item", "InventoryMaster"]
        for service_name in service_names:
            print(f"Step 4: Opening window '{service_name}'...")
            response = await client.post(
                f"{ui_server_url}/api/ui/interactive/v2/window",
                headers=headers,
                json={"ServiceName": service_name},
            )
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  WindowId: {data.get('WindowId')}")
                print(f"  SUCCESS!")
                # Close the window
                await client.delete(
                    f"{ui_server_url}/api/ui/interactive/v2/window",
                    headers=headers,
                    params={"windowId": data.get("WindowId")},
                )
                print(f"  (Window closed)")
            else:
                print(f"  Response: {response.text[:200]}")
            print()

        # End session
        print("Ending session...")
        await client.delete(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
        )
        print("Done!")


if __name__ == "__main__":
    asyncio.run(debug())
