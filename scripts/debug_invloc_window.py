"""Try InventoryLocation window."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print("Trying different windows for inv_loc")
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

        # List available services
        print("\n1. Listing services matching 'inv' or 'loc'...")
        response = await client.get(
            f"{ui_server_url}/api/v2/services",
            headers=headers,
        )
        if response.status_code == 200:
            services = response.json()
            print(f"   Response type: {type(services)}")
            if isinstance(services, dict):
                # Try to find the list of services
                print(f"   Keys: {services.keys()}")
                service_list = services.get("Services", services.get("value", []))
                if isinstance(service_list, list):
                    matching = [s.get("Name", s) if isinstance(s, dict) else s for s in service_list]
                    matching = [s for s in matching if isinstance(s, str) and ("inv" in s.lower() or "loc" in s.lower())]
                    print(f"   Found {len(matching)} matching services:")
                    for s in matching[:15]:
                        print(f"     - {s}")
            elif isinstance(services, list):
                matching = [s for s in services if isinstance(s, str) and ("inv" in s.lower() or "loc" in s.lower())]
                print(f"   Found {len(matching)} matching services:")
                for s in matching[:15]:
                    print(f"     - {s}")
        else:
            print(f"   Error: {response.status_code}")

        # Start session
        await client.post(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
            json={"ResponseWindowHandlingEnabled": False},
        )

        # Try different service names
        service_names = [
            "InventoryLocation",
            "InvLocation",
            "ItemLocation",
            "LocationItem",
            "InventoryLocations",
        ]

        for service in service_names:
            print(f"\n2. Trying to open '{service}'...")
            response = await client.post(
                f"{ui_server_url}/api/ui/interactive/v2/window",
                headers=headers,
                json={"ServiceName": service},
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                window_data = response.json()
                window_id = window_data.get("WindowId")
                print(f"   SUCCESS! WindowId: {window_id}")
                print(f"   DataElements: {[e.get('Name') for e in window_data.get('DataElements', [])][:5]}")

                # Close it
                await client.delete(
                    f"{ui_server_url}/api/ui/interactive/v2/window",
                    headers=headers,
                    params={"windowId": window_id},
                )
                break
            else:
                try:
                    err = response.json()
                    print(f"   Error: {err.get('ErrorMessage', response.text)[:100]}")
                except:
                    print(f"   Error: {response.text[:100]}")

        # End session
        await client.delete(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
        )

        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(debug())
