# Product Group Changer

JSON API for changing product groups in P21 inventory items.

## Overview

This API changes the product group for a single inventory item. It uses **optimistic locking** - you must assert the expected current product group, and the API will only proceed if it matches.

**Key Points:**
- Product groups in P21 are stored **per-location** in `inv_loc`, not on `inv_mast`
- All locations for an item must have the expected product group for validation to pass
- Changes are applied to ALL locations for the item
- Uses P21 Interactive API for reliable updates with full business logic

## Setup

### Windows Server

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scriptsctivate

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

```json
{
  "inv_mast_uid": 35923,
  "expected_product_group_id": "SU5S",
  "desired_product_group_id": "SU5B"
}
```

| Field | Description |
|-------|-------------|
| `inv_mast_uid` | Inventory master UID |
| `expected_product_group_id` | Current product group you expect (optimistic lock) |
| `desired_product_group_id` | Product group to change to |

### Response Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | Success | Update completed successfully |
| 400 | Bad Request | Item not found, no locations, invalid input |
| 409 | Conflict | Expected product group doesn't match actual (concurrency) |
| 500 | Server Error | Update failed (P21 error, record locked, etc.) |

### Example: Success (200)

```json
{
  "inv_mast_uid": 35923,
  "item_id": "GBY",
  "previous_product_group_id": "SU5S",
  "new_product_group_id": "SU5B",
  "locations_changed": [10, 19, 20, 30, 40, 50]
}
```

### Example: Concurrency Conflict (409)

Expected product group doesn't match - someone else changed it:

```json
{
  "error": "Concurrency conflict",
  "detail": "Expected 'SU5S' but found 'SU5B'"
}
```

### Example: Bad Request (400)

Item not found or has no locations:

```json
{
  "error": "Bad request",
  "detail": "Item not found"
}
```

### Example: Server Error (500)

Update failed during execution:

```json
{
  "error": "Update failed",
  "detail": "Location 30: Record locked by another user"
}
```

## Example Files

See `data/` folder for example payloads:

- `example-request.json` - Sample request
- `example-response-200-success.json` - Success response
- `example-response-400-bad-request.json` - Bad request
- `example-response-409-concurrency.json` - Concurrency conflict
- `example-response-500-server-error.json` - Server error

## Testing with curl

```powershell
# Windows PowerShell
$body = Get-Content -Raw data/example-request.json
Invoke-RestMethod -Uri "http://localhost:8000/api/change-product-group" -Method POST -Body $body -ContentType "application/json"
```

```bash
# Linux/Git Bash
curl -X POST http://localhost:8000/api/change-product-group   -H "Content-Type: application/json"   -d @data/example-request.json
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
