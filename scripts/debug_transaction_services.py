"""Explore Transaction API services for inv_loc."""

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
    print("Exploring Transaction API services")
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

        # List all services
        print("\n1. Listing available Transaction API services...")
        response = await client.get(
            f"{ui_server_url}/api/v2/services",
            headers=headers,
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            services = response.json()
            # Filter for inventory-related
            inv_services = [s for s in services if isinstance(s, str) and ("inv" in s.lower() or "item" in s.lower() or "loc" in s.lower())]
            print(f"   Inventory-related services: {inv_services}")

        # Get definition for Item
        print("\n2. Getting Item service definition (full)...")
        response = await client.get(
            f"{ui_server_url}/api/v2/definition/Item",
            headers=headers,
        )
        if response.status_code == 200:
            definition = response.json()
            # Print template structure
            template = definition.get("Template", {})
            if template:
                print("   Template DataElements:")
                for elem in template.get("DataElements", []):
                    print(f"     - {elem.get('Name')} (Type: {elem.get('Type')})")
                    if elem.get("Rows"):
                        row = elem["Rows"][0]
                        edits = row.get("Edits", [])[:5]
                        print(f"       Fields: {[e.get('Name') for e in edits]}...")

        # Get defaults for Item
        print("\n3. Getting Item defaults...")
        response = await client.get(
            f"{ui_server_url}/api/v2/defaults/Item",
            headers=headers,
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            defaults = response.json()
            # Print structure
            data_elements = defaults.get("DataElements", [])
            print(f"   Found {len(data_elements)} DataElements")
            for elem in data_elements[:5]:
                print(f"     - {elem.get('Name')}")

        # Try Transaction GET to retrieve an item
        print("\n4. Transaction GET to retrieve GBY...")
        get_payload = {
            "Name": "Item",
            "UseCodeValues": False,
            "Keys": [
                {"Name": "item_id", "Value": "GBY"}
            ]
        }
        response = await client.post(
            f"{ui_server_url}/api/v2/transaction/get",
            headers=headers,
            json=get_payload,
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Summary: {result.get('Summary')}")
            results = result.get("Results", {})
            transactions = results.get("Transactions", [])
            if transactions:
                for elem in transactions[0].get("DataElements", []):
                    name = elem.get("Name", "")
                    if "loc" in name.lower():
                        rows = elem.get("Rows", [])
                        print(f"   {name}: {len(rows)} rows")
                        if rows:
                            print(f"     Row 1 fields: {[e.get('Name') for e in rows[0].get('Edits', [])[:8]]}")
        else:
            try:
                err = response.json()
                print(f"   Error: {err.get('ErrorMessage', response.text[:200])}")
            except:
                print(f"   Response: {response.text[:300]}")

        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(debug())
