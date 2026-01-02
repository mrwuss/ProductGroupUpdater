"""Test Entity API for inv_loc updates."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print("Testing Entity API for inventory locations")
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

        # Try inventory endpoints
        endpoints = [
            "/api/inventory/locations",
            "/api/inventory/parts",
            "/api/inventory/parts/GBY",
            "/api/inventory/itemlocations",
            "/api/inventory/inventorylocations",
            "/api/data/inv_loc",  # Maybe direct table access
        ]

        for endpoint in endpoints:
            print(f"\nGET {endpoint}...")
            try:
                response = await client.get(
                    f"{BASE_URL}{endpoint}",
                    headers=headers,
                    params={"$query": "inv_mast_uid eq 35923"} if "inv_loc" in endpoint or "location" in endpoint.lower() else {},
                )
                print(f"  Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        print(f"  Results: {len(data)} items")
                        if data:
                            print(f"  Keys: {list(data[0].keys())[:10]}")
                    elif isinstance(data, dict):
                        print(f"  Keys: {list(data.keys())[:10]}")
                else:
                    print(f"  Response: {response.text[:200]}")
            except Exception as e:
                print(f"  Error: {e}")

        # Try REST API style
        print("\n\nTrying REST API style endpoints...")
        rest_endpoints = [
            f"/api/rest/v1/inv_loc",
            f"/api/rest/v2/inv_loc",
            f"/api/rest/inv_loc",
        ]

        for endpoint in rest_endpoints:
            print(f"\nGET {endpoint}...")
            try:
                response = await client.get(
                    f"{BASE_URL}{endpoint}",
                    headers=headers,
                    params={"filter": "inv_mast_uid eq 35923"},
                )
                print(f"  Status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"  Response type: {type(data)}")
                    if isinstance(data, dict):
                        print(f"  Keys: {list(data.keys())[:10]}")
            except Exception as e:
                print(f"  Error: {e}")

        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(debug())
