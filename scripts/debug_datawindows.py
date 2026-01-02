"""Debug Item window datawindows."""

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
    print("Checking Item window datawindows")
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

        # Start session
        await client.post(
            f"{ui_server_url}/api/ui/interactive/sessions/",
            headers=headers,
            json={"ResponseWindowHandlingEnabled": False},
        )

        # Open window and get DataElements
        print("\nOpening Item window...")
        response = await client.post(
            f"{ui_server_url}/api/ui/interactive/v2/window",
            headers=headers,
            json={"ServiceName": "Item"},
        )
        window_data = response.json()
        window_id = window_data.get("WindowId")
        print(f"Window ID: {window_id}")

        # Print all DataElements
        print("\nDataElements:")
        for elem in window_data.get("DataElements", []):
            name = elem.get("Name", "")
            table = elem.get("Table", "")
            print(f"  - {name} -> {table}")

        # Look for form-like elements
        print("\nForm datawindows (likely main form):")
        for elem in window_data.get("DataElements", []):
            name = elem.get("Name", "").lower()
            if "form" in name or "mast" in name or "header" in name:
                print(f"  - {elem.get('Name')} -> {elem.get('Table')}")

        # Try changing item_id on different datawindows
        form_candidates = ["d_form", "form", "inv_mast", "d_inv_mast", "d_header"]

        for dw in form_candidates:
            print(f"\nTrying item_id change on '{dw}'...")
            response = await client.put(
                f"{ui_server_url}/api/ui/interactive/v2/change",
                headers=headers,
                json={
                    "WindowId": window_id,
                    "ChangeRequests": [
                        {"DataWindowName": dw, "FieldName": "item_id", "Value": "GBY"}
                    ],
                },
            )
            result = response.json()
            status = result.get("Status")
            messages = result.get("Messages")
            events = result.get("Events")
            print(f"  Status: {status}, Messages: {messages}, Events: {events}")

            if status == 0 and not messages:
                # Check if we can now select a row
                print(f"  Trying row select...")
                row_response = await client.put(
                    f"{ui_server_url}/api/ui/interactive/v2/row",
                    headers=headers,
                    json={
                        "WindowId": window_id,
                        "DataWindowName": "invloclist",
                        "RowNumber": 1,
                    },
                )
                row_result = row_response.json()
                print(f"  Row select: Status={row_result.get('Status')}, Msg={row_result.get('Messages')}")

                # Try save to see if data is loaded
                print(f"  Trying Quick.Save...")
                save_response = await client.post(
                    f"{ui_server_url}/api/ui/interactive/v2/tools",
                    headers=headers,
                    json={"WindowId": window_id, "ToolName": "Quick.Save"},
                )
                save_result = save_response.json()
                print(f"  Save: Status={save_result.get('Status')}, Msg={save_result.get('Messages')}")
                break

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
