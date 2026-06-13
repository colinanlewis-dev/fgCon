"""
Run with: py test_combos.py
Tests the comboSettings table via direct Supabase connection and the local API.
"""
import sys
import json
import urllib.request
import urllib.error

BASE_URL = "http://localhost:8000"


def section(title):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print('='*50)


def ok(msg):
    print(f"  [PASS] {msg}")


def fail(msg):
    print(f"  [FAIL] {msg}")
    sys.exit(1)


# ── 1. Direct Supabase connection ────────────────────────────────────────────
section("1. Direct Supabase connection")

from database import supabase

payload = {"comboName": "_test_combo", "maxDrinkCost": 2.50, "maxSideCost": 1.25, "comboPrice": 8.99}
result = supabase.table("comboSettings").insert(payload).execute()
assert result.data, "Insert returned no data"
created = result.data[0]
combo_id = created["id"]
ok(f"Insert: id={combo_id}, comboPrice={created['comboPrice']}")

result = supabase.table("comboSettings").select("*").eq("id", combo_id).execute()
assert result.data, "Select returned no data"
assert result.data[0]["comboName"] == "_test_combo"
ok(f"Select: comboName='{result.data[0]['comboName']}'")

result = supabase.table("comboSettings").update({"comboPrice": 7.49}).eq("id", combo_id).execute()
assert result.data[0]["comboPrice"] == 7.49
ok(f"Update: comboPrice={result.data[0]['comboPrice']}")

supabase.table("comboSettings").delete().eq("id", combo_id).execute()
result = supabase.table("comboSettings").select("*").eq("id", combo_id).execute()
assert not result.data, "Row still exists after delete"
ok("Delete: row removed")


# ── 2. API endpoints (requires local server on :8000) ────────────────────────
section("2. API endpoints (requires: py -m uvicorn main:app --reload)")

def api(method, path, body=None):
    url = BASE_URL + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
                                  headers={"Content-Type": "application/json"} if body else {})
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read()
            return r.status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        body = e.read()
        return e.code, json.loads(body) if body else None

status, body = api("POST", "/api/combos", {
    "comboName": "_api_test_combo",
    "maxDrinkCost": 3.00,
    "maxSideCost": 1.00,
    "comboPrice": 10.49,
})
if status != 201:
    fail(f"POST /api/combos returned {status}: {body}")
api_id = body["id"]
ok(f"POST /api/combos: id={api_id}")

status, body = api("GET", "/api/combos")
assert status == 200
match = next((c for c in body if c["id"] == api_id), None)
assert match, "Created combo not found in GET /api/combos"
ok(f"GET /api/combos: found combo id={api_id}")

status, body = api("PUT", f"/api/combos/{api_id}", {"comboPrice": 9.00})
assert status == 200, f"PUT returned {status}: {body}"
assert body["comboPrice"] == 9.00
ok(f"PUT /api/combos/{api_id}: comboPrice={body['comboPrice']}")

status, _ = api("DELETE", f"/api/combos/{api_id}")
assert status == 204, f"DELETE returned {status}"
ok(f"DELETE /api/combos/{api_id}: removed")


section("All tests passed")
