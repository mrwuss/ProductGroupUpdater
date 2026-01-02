# Project: Product Group Changer

> JSON API for changing product groups in P21 inventory items with optimistic locking.

---

## Quick Context

This is an **API-only** service that changes product groups for inventory items in Prophet 21. It uses an optimistic locking pattern: the caller asserts what they believe the current product group is, and the API validates before making changes.

**Key Points:**
- Product groups in P21 are stored **per-location** in `inv_loc`, not on `inv_mast`
- All locations for an item must match the expected value (unless bypass enabled)
- Changes are applied to ALL locations for the item
- Uses P21 Interactive API for reliable updates

---

## Production

- **Server**: orderack-22
- **Port**: 8050
- **Service**: ProductGroupChanger (NSSM)
- **Path**: `c:\Services\product-group-changer`

---

## Key Files

| File | Purpose |
|------|---------|
| `src/product_group_changer/main.py` | FastAPI entry point |
| `src/product_group_changer/api/routes/product_groups.py` | Main endpoint |
| `src/product_group_changer/services/product_group_service.py` | Business logic |
| `src/product_group_changer/integrations/p21/client.py` | P21 Interactive API client |
| `src/product_group_changer/integrations/p21/odata.py` | P21 OData client |

---

## API Contract

### Endpoint

```
POST /api/change-product-group
```

### Request

```json
{
  "inv_mast_uid": 35923,
  "expected_product_group_id": "SU5S",
  "desired_product_group_id": "SU5B",
  "bypassConcurrency": false
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `inv_mast_uid` | Yes | Inventory master UID |
| `expected_product_group_id` | Yes | Current product group you expect (optimistic lock) |
| `desired_product_group_id` | Yes | Product group to change to |
| `bypassConcurrency` | No | Set `true` to skip concurrency check and force update |

### Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success - all locations updated |
| 400 | Bad request - item not found, no locations |
| 409 | Conflict - expected product group doesn't match actual |
| 422 | Validation error - missing/invalid fields |
| 500 | Server error - P21 update failed |

### Example Responses

**200 - Success:**
```json
{
  "inv_mast_uid": 35923,
  "item_id": "GBY",
  "previous_product_group_id": "SU5S",
  "new_product_group_id": "SU5B",
  "locations_changed": [10, 19, 20, 30, 40, 50]
}
```

**409 - Concurrency conflict:**
```json
{
  "error": "Concurrency conflict",
  "detail": "Location 19: expected 'SU5S' but found 'SU5B'"
}
```

**400 - Bad request:**
```json
{
  "error": "Bad request",
  "detail": "Item not found"
}
```

---

## P21 Interactive API Notes

Row selection uses `_internalrowindex` (1-based), not array index. The workflow:

1. Open Item window -> TABPAGE_1
2. Retrieve item by item_id
3. Navigate to Locations tab -> TABPAGE_17
4. Select row by `_internalrowindex`
5. Navigate to Location Detail -> TABPAGE_18
6. Change `product_group_id` field
7. Save

---

## Local Development

```powershell
cd C:\Projects\product-group-changer
.venv\Scriptsctivate
uvicorn product_group_changer.main:app --reload --port 8050
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `P21_BASE_URL` | Yes | P21 server URL (e.g., `https://play.ifpusa.com`) |
| `P21_USERNAME` | Yes | P21 API username |
| `P21_PASSWORD` | Yes | P21 API password |

---

*Last updated: 2026-01-02*
