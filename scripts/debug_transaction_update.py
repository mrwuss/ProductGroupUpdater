"""Test Transaction API for updating inv_loc product_group."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print("Testing Transaction API for inv_loc updates")
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

        # Get UI Server URL
        response = await client.get(
            f"{BASE_URL}/api/ui/router/v1?urlType=external",
            headers=headers,
        )
        ui_server_url = response.json().get("Url", "").rstrip("/")
        print(f"UI Server: {ui_server_url}")

        # First, check current value via OData
        print("\n1. Checking current product_group via OData...")
        response = await client.get(
            f"{BASE_URL}/odataservice/odata/table/inv_loc",
            headers=headers,
            params={
                "$filter": "inv_mast_uid eq 35923 and location_id eq 10",
                "$select": "product_group_id,item_id,location_id,inv_mast_uid",
            },
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("value"):
                record = data["value"][0]
                current_pg = record.get("product_group_id")
                print(f"   Current: item_id={record.get('item_id')}, location={record.get('location_id')}, product_group={current_pg}")

        # Get the Item service definition to understand the structure
        print("\n2. Getting Item service definition...")
        response = await client.get(
            f"{ui_server_url}/api/v2/definition/Item",
            headers=headers,
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            definition = response.json()
            # Find location-related data elements
            trans_def = definition.get("TransactionDefinition", {})
            data_elements = trans_def.get("DataElements", [])
            print(f"   Found {len(data_elements)} DataElements")
            for elem in data_elements:
                name = elem.get("Name", "").lower()
                if "loc" in name:
                    print(f"   - {elem.get('Name')} (Type: {elem.get('Type')}, Keys: {elem.get('Keys')})")

        # Try Transaction API UPDATE
        print("\n3. Attempting Transaction API update...")

        # Transaction API UPDATE payload
        # For updates, we need to include key fields to identify the record
        payload = {
            "Name": "Item",
            "UseCodeValues": False,
            "Transactions": [
                {
                    "Status": "Existing",  # Existing for updates
                    "DataElements": [
                        {
                            "Name": "TABPAGE_1.inv_mast",
                            "Type": "Form",
                            "Keys": ["item_id"],
                            "Rows": [
                                {
                                    "Edits": [
                                        {"Name": "item_id", "Value": "GBY"}
                                    ]
                                }
                            ]
                        },
                        {
                            "Name": "TABPAGE_17.invloclist",
                            "Type": "List",
                            "Keys": ["location_id"],
                            "Rows": [
                                {
                                    "Edits": [
                                        {"Name": "location_id", "Value": "10"},
                                        {"Name": "product_group_id", "Value": "SU5A"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        response = await client.post(
            f"{ui_server_url}/api/v2/transaction",
            headers=headers,
            json=payload,
        )
        print(f"   Status: {response.status_code}")
        try:
            result = response.json()
            print(f"   Messages: {result.get('Messages')}")
            print(f"   Summary: {result.get('Summary')}")
        except:
            print(f"   Response: {response.text[:500]}")

        # Verify if change happened
        print("\n4. Verifying change via OData...")
        response = await client.get(
            f"{BASE_URL}/odataservice/odata/table/inv_loc",
            headers=headers,
            params={
                "$filter": "inv_mast_uid eq 35923 and location_id eq 10",
                "$select": "product_group_id",
            },
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("value"):
                new_pg = data["value"][0].get("product_group_id")
                print(f"   product_group at loc 10: {new_pg}")

        print("\nDone!")


if __name__ == "__main__":
    asyncio.run(debug())
