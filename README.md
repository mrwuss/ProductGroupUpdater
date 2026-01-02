# Product Group Changer

JSON API for bulk product group changes in P21 inventory items.

## Overview

This API allows you to change product groups for multiple inventory items in a single request. It uses an **optimistic locking pattern** - you must assert the expected current product group for each item, and the API will only proceed if all assertions match.

**Key Points:**
- Product groups in P21 are stored **per-location** in `inv_loc`, not on `inv_mast`
- All locations for an item must have the expected product group for validation to pass
- Changes are applied to ALL locations for each item
- Uses P21 Interactive API for reliable updates with full business logic

## Setup

### Windows Server

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy and configure environment
copy .env.example .env
# Edit .env with your P21 credentials
```

### Environment Variables

```env
# P21 API Configuration
P21_BASE_URL=https://your-p21-server.com
P21_USERNAME=api_user
P21_PASSWORD=your_password

# Application Settings
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Server Settings
HOST=0.0.0.0
PORT=8000
```

## Running the API

```powershell
# Development
uvicorn product_group_changer.main:app --reload --port 8000

# Production
uvicorn product_group_changer.main:app --host 0.0.0.0 --port 8000
```

## API Usage

### Endpoint

```
POST /api/change-product-group
Content-Type: application/json
```

### Request Format

Each item specifies:
- `inv_mast_uid` - The inventory master UID
- `expected_product_group_id` - What you expect the current product group to be (for validation)
- `desired_product_group_id` - What you want to change it to

```json
{
  "items": [
    {
      "inv_mast_uid": 35923,
      "expected_product_group_id": "SU5S",
      "desired_product_group_id": "SU5B"
    },
    {
      "inv_mast_uid": 41502,
      "expected_product_group_id": "SU5S",
      "desired_product_group_id": "SU5B"
    }
  ]
}
```

### Response Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | All items validated AND all locations updated |
| 400 | Assertion Mismatch | Expected product group does not match actual (NO changes made) |
| 403 | Partial Failure | Assertions passed but some updates failed during execution |

### Example: Success (200)

All items changed successfully:

```json
{
  "total_changed": 2,
  "results": [
    {
      "inv_mast_uid": 35923,
      "item_id": "GBY",
      "previous_product_group_id": "SU5S",
      "new_product_group_id": "SU5B",
      "success": true,
      "locations_changed": [10, 19, 20, 30, 40, 50],
      "error": null
    }
  ]
}
```

### Example: Assertion Mismatch (400)

Validation failed - no changes were made:

```json
{
  "error": "Product group mismatch",
  "mismatches": [
    {
      "inv_mast_uid": 35923,
      "expected_product_group_id": "SU5S",
      "actual_product_group_id": "SU5B",
      "item_id": "GBY",
      "location_id": 10
    }
  ]
}
```

### Example: Partial Failure (403)

Some items updated, others failed:

```json
{
  "error": "Some updates failed",
  "total_requested": 10,
  "successful": 7,
  "failed": 3,
  "results": [
    {
      "inv_mast_uid": 35923,
      "item_id": "GBY",
      "previous_product_group_id": "SU5S",
      "new_product_group_id": "SU5B",
      "success": true,
      "locations_changed": [10, 19, 20, 30, 40, 50],
      "error": null
    },
    {
      "inv_mast_uid": 28741,
      "item_id": "HYD-PUMP-4500",
      "previous_product_group_id": "HY3A",
      "new_product_group_id": "HY3B",
      "success": false,
      "locations_changed": [10, 20],
      "error": "Location 30: Record locked by another user"
    }
  ]
}
```

## Example Files

See `data/` folder for complete example payloads:

- `example-request.json` - Sample request with 10 items
- `example-response-200-success.json` - All succeeded
- `example-response-400-assertion-mismatch.json` - Validation failed
- `example-response-403-partial-failure.json` - Some failed

## Testing with curl

```powershell
# Windows PowerShell
$body = Get-Content -Raw data/example-request.json
Invoke-RestMethod -Uri "http://localhost:8000/api/change-product-group" -Method POST -Body $body -ContentType "application/json"
```

```bash
# Linux/Git Bash
curl -X POST http://localhost:8000/api/change-product-group \
  -H "Content-Type: application/json" \
  -d @data/example-request.json
```

## Technical Details

### P21 Interactive API

This tool uses the P21 Interactive API (v2 endpoints) to make changes:

1. Opens Item window (Item service)
2. Retrieves item by item_id
3. Navigates to Locations tab (TABPAGE_17)
4. Selects correct location row by _internalrowindex
5. Navigates to Location Detail tab (TABPAGE_18)
6. Changes product_group_id field
7. Saves

### Why Interactive API?

- **Full business logic** - All P21 validation rules apply
- **Reliable updates** - Field-level control
- **Session-based** - Maintains state between operations

The Transaction API was considered but has known issues with updates (session pool contamination).
