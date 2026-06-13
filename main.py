from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from database import supabase

app = FastAPI()


class MenuItem(BaseModel):
    itemName: str
    itemCost: float
    itemType: str
    isAvailable: bool = True


class MenuItemUpdate(BaseModel):
    itemName: Optional[str] = None
    itemCost: Optional[float] = None
    itemType: Optional[str] = None
    isAvailable: Optional[bool] = None


@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/home.html", encoding="utf-8") as f:
        return f.read()


@app.get("/menu", response_class=HTMLResponse)
def menu_page():
    with open("templates/menu.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/menu")
def get_menu():
    result = supabase.table("menu").select("*").order("id").execute()
    return result.data


@app.post("/api/menu", status_code=201)
def create_item(item: MenuItem):
    result = supabase.table("menu").insert(item.model_dump()).execute()
    return result.data[0]


@app.put("/api/menu/{item_id}")
def update_item(item_id: int, item: MenuItemUpdate):
    updates = {k: v for k, v in item.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = supabase.table("menu").update(updates).eq("id", item_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item not found")
    return result.data[0]


@app.delete("/api/menu/{item_id}", status_code=204)
def delete_item(item_id: int):
    result = supabase.table("menu").delete().eq("id", item_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Item not found")


# --- Events ---

class Event(BaseModel):
    eventName: Optional[str] = None
    eventDate: str
    eventSize: Optional[str] = None
    isActive: bool = True


class EventUpdate(BaseModel):
    eventName: Optional[str] = None
    eventDate: Optional[str] = None
    eventSize: Optional[str] = None
    isActive: Optional[bool] = None


@app.get("/events", response_class=HTMLResponse)
def events_page():
    with open("templates/events.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/events")
def get_events():
    result = supabase.table("event").select("*").order("eventDate", desc=True).execute()
    return result.data


@app.get("/api/events/active")
def get_active_event():
    result = supabase.table("event").select("*").eq("isActive", True).limit(1).execute()
    return result.data[0] if result.data else None


@app.post("/api/events", status_code=201)
def create_event(event: Event):
    if event.isActive:
        supabase.table("event").update({"isActive": False}).eq("isActive", True).execute()
    result = supabase.table("event").insert(event.model_dump()).execute()
    return result.data[0]


@app.put("/api/events/{event_id}")
def update_event(event_id: int, event: EventUpdate):
    updates = {k: v for k, v in event.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if updates.get("isActive") is True:
        supabase.table("event").update({"isActive": False}).eq("isActive", True).execute()
    result = supabase.table("event").update(updates).eq("id", event_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Event not found")
    return result.data[0]


@app.delete("/api/events/{event_id}", status_code=204)
def delete_event(event_id: int):
    from postgrest.exceptions import APIError
    try:
        result = supabase.table("event").delete().eq("id", event_id).execute()
    except APIError as e:
        if e.code == "23503":
            raise HTTPException(status_code=409, detail="This event has orders and cannot be deleted.")
        raise
    if not result.data:
        raise HTTPException(status_code=404, detail="Event not found")


# --- Orders ---

class OrderItemIn(BaseModel):
    menuItemId: int
    quantity: int
    priceAtTime: float


class OrderIn(BaseModel):
    eventId: int
    items: list[OrderItemIn]
    isVIP: bool = False
    vipNote: Optional[str] = None
    usedCombo: bool = False


@app.get("/orders", response_class=HTMLResponse)
def orders_page():
    with open("templates/orders.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/orders")
def get_orders(eventId: int):
    orders = supabase.table("orders").select("*").eq("eventId", eventId).order("created_at", desc=True).execute()
    if not orders.data:
        return []
    order_ids = [o["id"] for o in orders.data]
    items = supabase.table("orderItems").select("*, menu(itemName)").in_("orderId", order_ids).execute()
    items_by_order: dict = {}
    for item in items.data:
        items_by_order.setdefault(item["orderId"], []).append(item)
    for order in orders.data:
        order["items"] = items_by_order.get(order["id"], [])
    return orders.data


@app.post("/api/orders", status_code=201)
def create_order(order: OrderIn):
    result = supabase.table("orders").insert({
        "eventId": order.eventId,
        "isVIP": order.isVIP,
        "vipNote": order.vipNote,
        "usedCombo": order.usedCombo,
    }).execute()
    new_order = result.data[0]
    price_override = 0.0 if order.isVIP else None
    order_items = [
        {
            "orderId": new_order["id"],
            "menuItemId": i.menuItemId,
            "quantity": i.quantity,
            "priceAtTime": price_override if price_override is not None else i.priceAtTime,
        }
        for i in order.items
    ]
    supabase.table("orderItems").insert(order_items).execute()
    return new_order


@app.delete("/api/orders/{order_id}", status_code=204)
def delete_order(order_id: int):
    supabase.table("orderItems").delete().eq("orderId", order_id).execute()
    result = supabase.table("orders").delete().eq("id", order_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")


# --- Combo Settings ---

class ComboSetting(BaseModel):
    comboName: str
    maxDrinkCost: float
    maxSideCost: float
    comboPrice: float


class ComboSettingUpdate(BaseModel):
    comboName: Optional[str] = None
    maxDrinkCost: Optional[float] = None
    maxSideCost: Optional[float] = None
    comboPrice: Optional[float] = None


@app.get("/combos", response_class=HTMLResponse)
def combos_page():
    with open("templates/combos.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/combos")
def get_combos():
    result = supabase.table("comboSettings").select("*").order("id").execute()
    return result.data


@app.post("/api/combos", status_code=201)
def create_combo(combo: ComboSetting):
    result = supabase.table("comboSettings").insert(combo.model_dump()).execute()
    return result.data[0]


@app.put("/api/combos/{combo_id}")
def update_combo(combo_id: int, combo: ComboSettingUpdate):
    updates = {k: v for k, v in combo.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = supabase.table("comboSettings").update(updates).eq("id", combo_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Combo not found")
    return result.data[0]


@app.delete("/api/combos/{combo_id}", status_code=204)
def delete_combo(combo_id: int):
    result = supabase.table("comboSettings").delete().eq("id", combo_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Combo not found")
