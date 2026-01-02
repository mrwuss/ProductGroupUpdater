# Project: Product Group Changer

> JSON API for bulk product group changes in P21 inventory items with optimistic locking.

---

## Quick Context

This is an **API-only** service that changes product groups for inventory items in Prophet 21. It uses an optimistic locking pattern: the caller asserts what they believe the current product group is, and the API validates before making changes.

---

## Key Files

| File | Purpose |
|------|---------|
| `src/product_group_changer/main.py` | FastAPI entry point |
| `src/product_group_changer/api/routes/product_groups.py` | Main endpoint |
| `src/product_group_changer/services/product_group_service.py` | Business logic |
| `src/product_group_changer/integrations/p21/` | P21 API clients |

---

## API Contract

### Endpoint

```
POST /api/change-product-group
```

### Request

```json
{
  "items": [
    {"inv_mast_uid": 12345, "expected_product_group_id": "FILTERS"},
    {"inv_mast_uid": 67890, "expected_product_group_id": "FILTERS"}
  ],
  "new_product_group_id": "FITTINGS"
}
```

### Responses

**200 - All changes succeeded:**
```json
{
  "total_changed": 2,
  "results": [
    {
      "inv_mast_uid": 12345,
      "item_id": "FILT-001",
      "previous_product_group_id": "FILTERS",
      "new_product_group_id": "FITTINGS",
      "success": true,
      "error": null
    },
    {
      "inv_mast_uid": 67890,
      "item_id": "FILT-002",
      "previous_product_group_id": "FILTERS",
      "new_product_group_id": "FITTINGS",
      "success": true,
      "error": null
    }
  ]
}
```

**400 - Assertion mismatch (no changes made):**
```json
{
  "error": "Product group mismatch",
  "mismatches": [
    {
      "inv_mast_uid": 12345,
      "expected_product_group_id": "FILTERS",
      "actual_product_group_id": "HOSE",
      "item_id": "FILT-001"
    }
  ]
}
```

**403 - Some updates failed:**
```json
{
  "error": "Some updates failed",
  "total_requested": 2,
  "successful": 1,
  "failed": 1,
  "results": [
    {
      "inv_mast_uid": 12345,
      "item_id": "FILT-001",
      "previous_product_group_id": "FILTERS",
      "new_product_group_id": "FITTINGS",
      "success": true,
      "error": null
    },
    {
      "inv_mast_uid": 67890,
      "item_id": "FILT-002",
      "previous_product_group_id": "FILTERS",
      "new_product_group_id": "FITTINGS",
      "success": false,
      "error": "P21 validation error: ..."
    }
  ]
}
```

---

## Workflow

```
1. Receive request with items + assertions + target product group
         │
         ▼
2. Validate ALL items match their asserted product groups (OData)
         │
         ├─ ANY mismatch? → 400 + mismatch details (NO changes made)
         │
         ▼
3. Update ALL items to new product group (Interactive API)
         │
         ├─ ALL succeed? → 200 + results
         │
         └─ ANY fail? → 403 + individual results
```

---

## P21 API Usage

| API | Usage |
|-----|-------|
| **OData** | Validate assertions (read current product groups) |
| **Interactive** | Update product groups (reliable updates with validation) |

---

## Testing

```bash
pytest
pytest --cov=src
```

---

## Local Development

```bash
cp .env.example .env
pip install -e ".[dev]"
uvicorn src.product_group_changer.main:app --reload --port 8000

# API docs: http://localhost:8000/docs
```

---

## Example curl

```bash
curl -X POST http://localhost:8000/api/change-product-group \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"inv_mast_uid": 12345, "expected_product_group_id": "FILTERS"},
      {"inv_mast_uid": 67890, "expected_product_group_id": "FILTERS"}
    ],
    "new_product_group_id": "FITTINGS"
  }'
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `P21_BASE_URL` | Yes | P21 server URL |
| `P21_USERNAME` | Yes | P21 API username |
| `P21_PASSWORD` | Yes | P21 API password |

---

*Last updated: 2026-01-02*
