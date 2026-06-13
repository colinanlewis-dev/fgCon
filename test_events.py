"""
Run with: py test_events.py
Tests:
  1. An event with linked orders CANNOT be deleted (FK constraint protects order data)
  2. An event with no orders CAN be deleted
  3. A new event created after deletion receives a fresh, non-repeating ID
"""
import sys
from postgrest.exceptions import APIError
from database import supabase


def ok(msg):     print(f"  [PASS] {msg}")
def info(msg):   print(f"  [INFO] {msg}")
def fail(msg):   print(f"  [FAIL] {msg}"); sys.exit(1)
def section(t):  print(f"\n{'='*55}\n  {t}\n{'='*55}")


# ── Setup ─────────────────────────────────────────────────────────────────────
section("Setup")

menu_res = supabase.table("menu").insert({
    "itemName": "_test_item", "itemCost": 1.00,
    "itemType": "Side", "isAvailable": True,
}).execute()
menu_id = menu_res.data[0]["id"]
ok(f"Created temp menu item id={menu_id}")

event_res = supabase.table("event").insert({
    "eventName": "_test_event_A", "eventDate": "2099-01-01", "isActive": False,
}).execute()
event_a_id = event_res.data[0]["id"]
ok(f"Created Event A id={event_a_id}")

order_res = supabase.table("orders").insert({
    "eventId": event_a_id, "isVIP": False, "usedCombo": False,
}).execute()
order_id = order_res.data[0]["id"]
ok(f"Created order id={order_id} linked to Event A")

item_res = supabase.table("orderItems").insert({
    "orderId": order_id, "menuItemId": menu_id,
    "quantity": 1, "priceAtTime": 1.00,
}).execute()
order_item_id = item_res.data[0]["id"]
ok(f"Created orderItem id={order_item_id}")


# ── Test 1: Deleting an event with orders is BLOCKED ─────────────────────────
section("1. Event with orders cannot be deleted (FK protection)")

try:
    supabase.table("event").delete().eq("id", event_a_id).execute()
    fail("Event A was deleted despite having linked orders — orders are unprotected!")
except APIError as e:
    if "foreign key constraint" in e.message.lower() or e.code == "23503":
        ok(f"Deletion blocked by FK constraint — orders are safe (code={e.code})")
        info(f"Constraint: {e.message}")
    else:
        fail(f"Unexpected error: {e.message}")

# Confirm event and orders still intact
assert supabase.table("event").select("id").eq("id", event_a_id).execute().data, \
    "Event A unexpectedly missing"
assert supabase.table("orders").select("id").eq("id", order_id).execute().data, \
    "Order unexpectedly missing"
ok("Event A and its orders confirmed still present")


# ── Test 2: Event WITHOUT orders can be deleted ───────────────────────────────
section("2. Event with no orders can be deleted")

event_b_res = supabase.table("event").insert({
    "eventName": "_test_event_B", "eventDate": "2099-02-01", "isActive": False,
}).execute()
event_b_id = event_b_res.data[0]["id"]
ok(f"Created Event B (no orders) id={event_b_id}")

supabase.table("event").delete().eq("id", event_b_id).execute()
gone = supabase.table("event").select("id").eq("id", event_b_id).execute()
assert not gone.data, "Event B still exists after deletion"
ok(f"Event B id={event_b_id} deleted successfully")


# ── Test 3: New event gets a non-repeating ID ─────────────────────────────────
section("3. New event ID does not repeat deleted ID")

event_c_res = supabase.table("event").insert({
    "eventName": "_test_event_C", "eventDate": "2099-03-01", "isActive": False,
}).execute()
event_c_id = event_c_res.data[0]["id"]
ok(f"Created Event C id={event_c_id}")

if event_c_id == event_b_id:
    fail(f"Event C reused deleted Event B's id={event_b_id} — sequence reset!")
if event_c_id < event_b_id:
    fail(f"Event C id={event_c_id} is lower than deleted Event B id={event_b_id}")
ok(f"Event C id={event_c_id} is unique and greater than deleted Event B id={event_b_id}")


# ── Cleanup ───────────────────────────────────────────────────────────────────
section("Cleanup")

supabase.table("orderItems").delete().eq("id", order_item_id).execute()
ok(f"Deleted orderItem id={order_item_id}")
supabase.table("orders").delete().eq("id", order_id).execute()
ok(f"Deleted order id={order_id}")
supabase.table("event").delete().eq("id", event_a_id).execute()
ok(f"Deleted Event A id={event_a_id} (now safe, no orders)")
supabase.table("event").delete().eq("id", event_c_id).execute()
ok(f"Deleted Event C id={event_c_id}")
supabase.table("menu").delete().eq("id", menu_id).execute()
ok(f"Deleted temp menu item id={menu_id}")

section("All tests passed")
print("""
Summary:
  - Events with linked orders are PROTECTED by FK constraint — deletion is blocked
  - Events with no orders can be deleted freely
  - PostgreSQL sequences never reuse IDs — new events always get a fresh ID
  - To delete an event that has orders: delete the orders first, then the event
""")
