"""Verify product_group change via OData."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def verify():
    print("Verifying product_group via OData")
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
            "Accept": "application/json",
        }

        # Query inv_loc for item 35923 (GBY)
        print("\nQuerying inv_loc for inv_mast_uid 35923:")
        response = await client.get(
            f"{BASE_URL}/odataservice/odata/table/inv_loc",
            headers=headers,
            params={
                "$filter": "inv_mast_uid eq 35923",
                "$select": "location_id,product_group_id,inv_mast_uid",
            },
        )

        if response.status_code == 200:
            data = response.json()
            for row in data.get("value", []):
                loc = row.get("location_id")
                pg = row.get("product_group_id")
                print(f"  Location {loc}: product_group = {pg}")
        else:
            print(f"OData error: {response.status_code}")
            print(response.text[:200])


if __name__ == "__main__":
    asyncio.run(verify())
