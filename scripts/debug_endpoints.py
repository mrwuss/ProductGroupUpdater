"""Test different endpoint versions."""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("P21_BASE_URL", "https://play.ifpusa.com")
USERNAME = os.getenv("P21_USERNAME")
PASSWORD = os.getenv("P21_PASSWORD")


async def debug():
    print(f"Testing endpoint variations")
    print(f"=" * 60)

    async with httpx.AsyncClient(verify=False, timeout=60.0, follow_redirects=True) as client:
        # Authenticate
        response = await client.post(
            f"{BASE_URL}/api/security/token/v2",
            json={"username": USERNAME, "password": PASSWORD},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
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
        response.raise_for_status()
        ui_server_url = response.json().get("Url", "").rstrip("/")
        print(f"UI Server: {ui_server_url}\n")

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
        print(f"Open Window (v2): {response.status_code}")
        window_data = response.json() if response.status_code == 200 else {}
        window_id = window_data.get("WindowId", "test")

        # Test different change endpoint URLs
        change_body = {
            "WindowId": window_id,
            "ChangeRequests": [
                {
                    "DataWindowName": "d_form",
                    "FieldName": "item_id",
                    "Value": "GBY",
                }
            ],
        }

        endpoints = [
            f"{ui_server_url}/api/ui/interactive/v1/change",
            f"{ui_server_url}/api/ui/interactive/v2/change",
            f"{ui_server_url}/api/ui/interactive/change",
            f"{ui_server_url}/api/ui/interactive/v1/data/change",
            f"{ui_server_url}/api/ui/interactive/v2/data/change",
        ]

        print("\nTesting change endpoints:")
        for endpoint in endpoints:
            try:
                response = await client.put(endpoint, headers=headers, json=change_body)
                print(f"  PUT {endpoint.split('/uiserver0')[1]}: {response.status_code}")
                if response.status_code == 200:
                    print(f"      SUCCESS! Response: {response.text[:200]}")
            except Exception as e:
                print(f"  PUT {endpoint.split('/uiserver0')[1]}: ERROR - {e}")

        # Test data endpoint (which we know works for GET)
        print("\nTesting data endpoints:")
        data_body = {"WindowId": window_id}

        data_endpoints = [
            (f"{ui_server_url}/api/ui/interactive/v1/data", "PUT"),
            (f"{ui_server_url}/api/ui/interactive/v2/data", "PUT"),
            (f"{ui_server_url}/api/ui/interactive/v1/data", "GET"),
            (f"{ui_server_url}/api/ui/interactive/v2/data", "GET"),
        ]

        for endpoint, method in data_endpoints:
            try:
                if method == "PUT":
                    response = await client.put(endpoint, headers=headers, json=data_body)
                else:
                    response = await client.get(endpoint, headers=headers, params={"windowId": window_id})
                print(f"  {method} {endpoint.split('/uiserver0')[1]}: {response.status_code}")
            except Exception as e:
                print(f"  {method} {endpoint.split('/uiserver0')[1]}: ERROR - {e}")

        # Test tab endpoint
        print("\nTesting tab endpoints:")
        tab_body = {"WindowId": window_id, "PagePath": {"PageName": "TABPAGE_17"}}
        tab_endpoints = [
            f"{ui_server_url}/api/ui/interactive/v1/tab",
            f"{ui_server_url}/api/ui/interactive/v2/tab",
        ]
        for endpoint in tab_endpoints:
            try:
                response = await client.put(endpoint, headers=headers, json=tab_body)
                print(f"  PUT {endpoint.split('/uiserver0')[1]}: {response.status_code}")
            except Exception as e:
                print(f"  PUT {endpoint.split('/uiserver0')[1]}: ERROR - {e}")

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
