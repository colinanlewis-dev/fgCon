import hmac
import hashlib
import json
import os
import time
import urllib.request
from datetime import date

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from database import supabase

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Auth helpers ---

_SECRET = os.environ.get("APP_SECRET", "dev-secret-change-me")
_PASSWORD = os.environ.get("APP_PASSWORD", "")

def _make_token() -> str:
    ts = str(int(time.time()))
    sig = hmac.new(_SECRET.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"

def _verify_token(token: str) -> bool:
    try:
        ts, sig = token.split(".", 1)
        expected = hmac.new(_SECRET.encode(), ts.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        return (time.time() - int(ts)) < 86400 * 30  # 30-day sessions
    except Exception:
        return False

_PUBLIC_PATHS = {"/login", "/api/login", "/manifest.json", "/sw.js"}


@app.get("/manifest.json")
def serve_manifest():
    return FileResponse("static/manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
def serve_sw():
    return FileResponse("static/sw.js", media_type="application/javascript")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)
    token = request.cookies.get("session")
    if not token or not _verify_token(token):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return RedirectResponse(f"/login?next={request.url.path}", status_code=302)
    return await call_next(request)


_USERNAME = "Glen-Admin"


class LoginIn(BaseModel):
    username: str
    password: str


@app.get("/login", response_class=HTMLResponse)
def login_page():
    with open("templates/login.html", encoding="utf-8") as f:
        return f.read()


@app.post("/api/login")
def do_login(body: LoginIn, response: Response):
    expected = _PASSWORD
    username_ok = hmac.compare_digest(body.username, _USERNAME)
    password_ok = bool(expected) and hmac.compare_digest(body.password, expected)
    if not username_ok or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = _make_token()
    response.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400 * 30)
    return {"ok": True}


@app.post("/api/logout")
def do_logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}


class MenuType(BaseModel):
    menuName: str


class MenuTypeUpdate(BaseModel):
    menuName: Optional[str] = None


class MenuItem(BaseModel):
    itemName: str
    itemCost: float
    itemType: str
    isAvailable: bool = True
    menuTypeId: Optional[int] = None
    isComboSnack: bool = False
    isComboMain: bool = False


class MenuItemUpdate(BaseModel):
    itemName: Optional[str] = None
    itemCost: Optional[float] = None
    itemType: Optional[str] = None
    isAvailable: Optional[bool] = None
    menuTypeId: Optional[int] = None
    isComboSnack: Optional[bool] = None
    isComboMain: Optional[bool] = None


@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/home.html", encoding="utf-8") as f:
        return f.read()


@app.get("/menu", response_class=HTMLResponse)
def menu_page():
    with open("templates/menu.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/menu-types")
def get_menu_types():
    result = supabase.table("menuType").select("*").order("id").execute()
    return result.data


@app.post("/api/menu-types", status_code=201)
def create_menu_type(menu_type: MenuType):
    result = supabase.table("menuType").insert(menu_type.model_dump()).execute()
    return result.data[0]


@app.put("/api/menu-types/{type_id}")
def update_menu_type(type_id: int, menu_type: MenuTypeUpdate):
    updates = {k: v for k, v in menu_type.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = supabase.table("menuType").update(updates).eq("id", type_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Menu type not found")
    return result.data[0]


@app.delete("/api/menu-types/{type_id}", status_code=204)
def delete_menu_type(type_id: int):
    result = supabase.table("menuType").delete().eq("id", type_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Menu type not found")


@app.get("/api/menu")
def get_menu(menuTypeId: Optional[int] = None):
    query = supabase.table("menu").select("*, menuType(menuName)").order("id")
    if menuTypeId is not None:
        query = query.eq("menuTypeId", menuTypeId)
    result = query.execute()
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
    homeTeamSize: Optional[int] = None
    awayTeamSize: Optional[int] = None
    meetWeather: Optional[str] = None
    meetNotes: Optional[str] = None
    meetPrep: Optional[str] = None
    eventSeedMoney: Optional[float] = None
    meetCost: Optional[float] = None
    isActive: bool = True
    menuTypeID: int


class EventUpdate(BaseModel):
    eventName: Optional[str] = None
    eventDate: Optional[str] = None
    homeTeamSize: Optional[int] = None
    awayTeamSize: Optional[int] = None
    meetWeather: Optional[str] = None
    meetNotes: Optional[str] = None
    meetPrep: Optional[str] = None
    eventSeedMoney: Optional[float] = None
    meetCost: Optional[float] = None
    isActive: Optional[bool] = None
    menuTypeID: Optional[int] = None


@app.get("/events", response_class=HTMLResponse)
def events_page():
    with open("templates/events.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/events")
def get_events():
    result = supabase.table("event").select("*, menuType(menuName)").order("eventDate", desc=True).execute()
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


_WMO_CODES = {
    0: "Clear Sky",
    1: "Mostly Clear", 2: "Partly Cloudy", 3: "Overcast",
    45: "Foggy", 48: "Foggy",
    51: "Light Drizzle", 53: "Drizzle", 55: "Heavy Drizzle",
    61: "Light Rain", 63: "Rain", 65: "Heavy Rain",
    71: "Light Snow", 73: "Snow", 75: "Heavy Snow", 77: "Snow Grains",
    80: "Light Showers", 81: "Showers", 82: "Heavy Showers",
    85: "Snow Showers", 86: "Heavy Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ Hail", 99: "Thunderstorm w/ Hail",
}
_MEET_LAT = 42.457963
_MEET_LON = -83.378611

def _fetch_weather(event_date_str: str) -> Optional[str]:
    """Fetch weather for any date — archive for past, forecast for future/today."""
    try:
        is_past = date.fromisoformat(event_date_str) < date.today()
        if is_past:
            base = "https://archive-api.open-meteo.com/v1/archive"
        else:
            base = "https://api.open-meteo.com/v1/forecast"
        url = (
            f"{base}?latitude={_MEET_LAT}&longitude={_MEET_LON}"
            "&daily=temperature_2m_max,temperature_2m_min,weathercode"
            "&temperature_unit=fahrenheit&timezone=America%2FDetroit"
            f"&start_date={event_date_str}&end_date={event_date_str}"
        )
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
        daily = data["daily"]
        hi   = round(daily["temperature_2m_max"][0])
        lo   = round(daily["temperature_2m_min"][0])
        cond = _WMO_CODES.get(int(daily["weathercode"][0]), "Unknown")
        return f"Hi {hi}°F / Lo {lo}°F, {cond}"
    except Exception:
        return None


@app.put("/api/events/{event_id}")
def update_event(event_id: int, event: EventUpdate):
    updates = {k: v for k, v in event.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if updates.get("isActive") is True:
        supabase.table("event").update({"isActive": False}).eq("isActive", True).execute()
    # Auto-fill weather when deactivating (forecast for future, archive for past)
    if updates.get("isActive") is False:
        ev = supabase.table("event").select("eventDate").eq("id", event_id).execute()
        if ev.data:
            weather = _fetch_weather(ev.data[0]["eventDate"])
            if weather:
                updates["meetWeather"] = weather
    result = supabase.table("event").update(updates).eq("id", event_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Event not found")
    return result.data[0]


@app.post("/api/events/{event_id}/refresh-weather")
def refresh_event_weather(event_id: int):
    ev = supabase.table("event").select("eventDate").eq("id", event_id).execute()
    if not ev.data:
        raise HTTPException(status_code=404, detail="Event not found")
    weather = _fetch_weather(ev.data[0]["eventDate"])
    if not weather:
        raise HTTPException(status_code=422, detail="Could not fetch weather for this date")
    result = supabase.table("event").update({"meetWeather": weather}).eq("id", event_id).execute()
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
    vipTeam: Optional[str] = None
    usedCombo: bool = False
    paymentMethod: Optional[str] = None


@app.get("/orders", response_class=HTMLResponse)
def orders_page():
    with open("templates/orders.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/orders/init")
def orders_init():
    from concurrent.futures import ThreadPoolExecutor

    event_res = supabase.table("event").select("*").eq("isActive", True).limit(1).execute()
    if not event_res.data:
        return {"event": None, "menu": [], "combos": []}
    event = event_res.data[0]
    menu_type_id = event.get("menuTypeID")

    def get_menu():
        q = supabase.table("menu").select("*").eq("isAvailable", True).order("id")
        if menu_type_id:
            q = q.eq("menuTypeId", menu_type_id)
        return q.execute().data

    def get_combos():
        return supabase.table("comboSettings").select("*").order("id").execute().data

    with ThreadPoolExecutor(max_workers=2) as ex:
        menu_f, combos_f = ex.submit(get_menu), ex.submit(get_combos)
        menu, combos = menu_f.result(), combos_f.result()

    return {"event": event, "menu": menu, "combos": combos}


@app.get("/api/orders/popular")
def get_popular_items(eventId: int):
    orders = supabase.table("orders").select("id").eq("eventId", eventId).execute()
    if not orders.data:
        return []
    order_ids = [o["id"] for o in orders.data]
    items = supabase.table("orderItems").select("menuItemId, quantity, menu(itemName)").in_("orderId", order_ids).execute()
    totals: dict = {}
    for i in items.data:
        mid = i["menuItemId"]
        if mid not in totals:
            totals[mid] = {"id": mid, "name": i["menu"]["itemName"] if i["menu"] else "Item", "qty": 0}
        totals[mid]["qty"] += i["quantity"]
    return sorted(totals.values(), key=lambda x: x["qty"], reverse=True)[:5]


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
        "vipTeam": order.vipTeam,
        "usedCombo": order.usedCombo,
        "paymentMethod": order.paymentMethod,
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


@app.get("/api/orders/{order_id}")
def get_order(order_id: int):
    result = supabase.table("orders").select("*").eq("id", order_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")
    order = result.data[0]
    items = supabase.table("orderItems").select("*, menu(id, itemName, itemCost, itemType)").eq("orderId", order_id).execute()
    order["items"] = items.data
    return order


class OrderUpdateIn(BaseModel):
    items: list[OrderItemIn]
    isVIP: bool = False
    vipNote: Optional[str] = None
    vipTeam: Optional[str] = None
    usedCombo: bool = False
    paymentMethod: Optional[str] = None


@app.put("/api/orders/{order_id}")
def update_order(order_id: int, order: OrderUpdateIn):
    result = supabase.table("orders").select("id").eq("id", order_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")
    supabase.table("orders").update({
        "isVIP": order.isVIP,
        "vipNote": order.vipNote,
        "vipTeam": order.vipTeam,
        "usedCombo": order.usedCombo,
        "paymentMethod": order.paymentMethod,
    }).eq("id", order_id).execute()
    supabase.table("orderItems").delete().eq("orderId", order_id).execute()
    price_override = 0.0 if order.isVIP else None
    if order.items:
        supabase.table("orderItems").insert([
            {
                "orderId": order_id,
                "menuItemId": i.menuItemId,
                "quantity": i.quantity,
                "priceAtTime": price_override if price_override is not None else i.priceAtTime,
            }
            for i in order.items
        ]).execute()
    return {"id": order_id}


@app.delete("/api/orders/{order_id}", status_code=204)
def delete_order(order_id: int):
    supabase.table("orderItems").delete().eq("orderId", order_id).execute()
    result = supabase.table("orders").delete().eq("id", order_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Order not found")


# --- Reports ---

@app.get("/reports", response_class=HTMLResponse)
def reports_page():
    with open("templates/reports.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/reports/vip/{event_id}")
def get_vip_report(event_id: int):
    event = supabase.table("event").select("*").eq("id", event_id).execute()
    if not event.data:
        raise HTTPException(status_code=404, detail="Event not found")
    orders = supabase.table("orders").select("id, vipTeam, vipNote, created_at").eq("eventId", event_id).eq("isVIP", True).order("vipTeam").order("created_at").execute()
    if not orders.data:
        return {"event": event.data[0], "orders": []}
    order_ids = [o["id"] for o in orders.data]
    items = supabase.table("orderItems").select("orderId, quantity, menu(itemName)").in_("orderId", order_ids).execute()
    items_by_order: dict = {}
    for i in items.data:
        items_by_order.setdefault(i["orderId"], []).append(i)
    result = []
    for o in orders.data:
        order_items = items_by_order.get(o["id"], [])
        summary = ", ".join(
            f"{i['quantity']}x {i['menu']['itemName']}" if i["menu"] else f"{i['quantity']}x Item"
            for i in order_items
        )
        result.append({
            "id": o["id"],
            "vipTeam": o.get("vipTeam") or "—",
            "vipNote": o.get("vipNote") or "",
            "items": summary,
            "createdAt": o.get("created_at"),
        })
    return {"event": event.data[0], "orders": result}


@app.get("/api/reports/event/{event_id}")
def get_event_report(event_id: int):
    event = supabase.table("event").select("*, menuType(menuName)").eq("id", event_id).execute()
    if not event.data:
        raise HTTPException(status_code=404, detail="Event not found")

    orders = supabase.table("orders").select("*").eq("eventId", event_id).execute()
    if not orders.data:
        return {"event": event.data[0], "summary": {"totalRevenue": 0, "orderCount": 0, "vipOrders": 0, "comboOrders": 0, "paymentBreakdown": {}}, "itemBreakdown": [], "typeBreakdown": {}}

    order_ids = [o["id"] for o in orders.data]
    items = supabase.table("orderItems").select("*, menu(itemName, itemType)").in_("orderId", order_ids).execute()

    total_revenue = sum(i["priceAtTime"] * i["quantity"] for i in items.data)
    vip_orders = sum(1 for o in orders.data if o["isVIP"])
    combo_orders = sum(1 for o in orders.data if o["usedCombo"])

    order_revenue = {}
    for i in items.data:
        order_revenue[i["orderId"]] = order_revenue.get(i["orderId"], 0.0) + i["priceAtTime"] * i["quantity"]

    payment_breakdown: dict = {}
    for o in orders.data:
        pm = o.get("paymentMethod") or "Unknown"
        if pm not in payment_breakdown:
            payment_breakdown[pm] = {"count": 0, "revenue": 0.0}
        payment_breakdown[pm]["count"] += 1
        payment_breakdown[pm]["revenue"] += order_revenue.get(o["id"], 0.0)

    cash_revenue = payment_breakdown.get("Cash", {}).get("revenue", 0.0)

    runners = supabase.table("runner").select("runnerCost").eq("eventId", event_id).execute()
    runner_total = sum(r["runnerCost"] for r in runners.data if r["runnerCost"] is not None)

    seed_money = event.data[0].get("eventSeedMoney") or 0.0
    cashbox_total = cash_revenue + seed_money - runner_total

    item_totals: dict = {}
    for i in items.data:
        mid = i["menuItemId"]
        if mid not in item_totals:
            item_totals[mid] = {"name": i["menu"]["itemName"] if i["menu"] else "Unknown", "type": i["menu"]["itemType"] if i["menu"] else "Unknown", "qty": 0, "revenue": 0.0}
        item_totals[mid]["qty"] += i["quantity"]
        item_totals[mid]["revenue"] += i["priceAtTime"] * i["quantity"]

    type_totals: dict = {}
    for item in item_totals.values():
        t = item["type"]
        if t not in type_totals:
            type_totals[t] = {"qty": 0, "revenue": 0.0}
        type_totals[t]["qty"] += item["qty"]
        type_totals[t]["revenue"] += item["revenue"]

    return {
        "event": event.data[0],
        "summary": {
            "totalRevenue": total_revenue,
            "orderCount": len(orders.data),
            "vipOrders": vip_orders,
            "comboOrders": combo_orders,
            "paymentBreakdown": payment_breakdown,
            "cashRevenue": cash_revenue,
            "seedMoney": seed_money,
            "runnerTotal": runner_total,
            "cashboxTotal": cashbox_total,
        },
        "itemBreakdown": sorted(item_totals.values(), key=lambda x: x["revenue"], reverse=True),
        "typeBreakdown": type_totals,
    }


@app.get("/api/reports/season/{year}")
def get_season_report(year: int):
    events = supabase.table("event").select("*").gte("eventDate", f"{year}-01-01").lte("eventDate", f"{year}-12-31").order("eventDate").execute()
    if not events.data:
        return {"year": year, "summary": {"totalRevenue": 0, "totalOrders": 0, "eventCount": 0, "vipOrders": 0, "comboOrders": 0, "paymentBreakdown": {}}, "events": [], "topItems": []}

    event_ids = [e["id"] for e in events.data]
    orders = supabase.table("orders").select("*").in_("eventId", event_ids).execute()
    order_ids = [o["id"] for o in orders.data] if orders.data else []

    items_data = []
    if order_ids:
        items = supabase.table("orderItems").select("*, menu(itemName, itemType)").in_("orderId", order_ids).execute()
        items_data = items.data

    event_map = {e["id"]: {**e, "revenue": 0.0, "orderCount": 0} for e in events.data}
    order_event_map = {o["id"]: o["eventId"] for o in orders.data} if orders.data else {}

    for o in (orders.data or []):
        event_map[o["eventId"]]["orderCount"] += 1
    for i in items_data:
        eid = order_event_map.get(i["orderId"])
        if eid and eid in event_map:
            event_map[eid]["revenue"] += i["priceAtTime"] * i["quantity"]

    order_revenue = {}
    for i in items_data:
        order_revenue[i["orderId"]] = order_revenue.get(i["orderId"], 0.0) + i["priceAtTime"] * i["quantity"]

    payment_breakdown: dict = {}
    for o in (orders.data or []):
        pm = o.get("paymentMethod") or "Unknown"
        if pm not in payment_breakdown:
            payment_breakdown[pm] = {"count": 0, "revenue": 0.0}
        payment_breakdown[pm]["count"] += 1
        payment_breakdown[pm]["revenue"] += order_revenue.get(o["id"], 0.0)

    item_totals: dict = {}
    for i in items_data:
        mid = i["menuItemId"]
        if mid not in item_totals:
            item_totals[mid] = {"name": i["menu"]["itemName"] if i["menu"] else "Unknown", "type": i["menu"]["itemType"] if i["menu"] else "Unknown", "qty": 0, "revenue": 0.0}
        item_totals[mid]["qty"] += i["quantity"]
        item_totals[mid]["revenue"] += i["priceAtTime"] * i["quantity"]

    runners = supabase.table("runner").select("runnerCost").in_("eventId", event_ids).execute()
    total_runner_cost = sum(r["runnerCost"] for r in runners.data if r["runnerCost"] is not None)

    total_revenue = sum(e["revenue"] for e in event_map.values())
    total_meet_cost = sum(e.get("meetCost") or 0.0 for e in event_map.values())

    return {
        "year": year,
        "summary": {
            "totalRevenue": total_revenue,
            "totalOrders": sum(e["orderCount"] for e in event_map.values()),
            "eventCount": len(events.data),
            "vipOrders": sum(1 for o in (orders.data or []) if o["isVIP"]),
            "comboOrders": sum(1 for o in (orders.data or []) if o["usedCombo"]),
            "paymentBreakdown": payment_breakdown,
            "totalMeetCost": total_meet_cost,
            "totalRunnerCost": total_runner_cost,
            "totalProfit": total_revenue - total_meet_cost - total_runner_cost,
        },
        "events": list(event_map.values()),
        "topItems": sorted(item_totals.values(), key=lambda x: x["revenue"], reverse=True)[:10],
    }


# --- Runners ---

class Runner(BaseModel):
    eventId: int
    runnerItems: Optional[str] = None
    runnerCost: Optional[float] = None


class RunnerUpdate(BaseModel):
    eventId: Optional[int] = None
    runnerItems: Optional[str] = None
    runnerCost: Optional[float] = None


@app.get("/runners", response_class=HTMLResponse)
def runners_page():
    with open("templates/runners.html", encoding="utf-8") as f:
        return f.read()


@app.get("/api/runners")
def get_runners(eventId: Optional[int] = None):
    q = supabase.table("runner").select("*, event(eventName, eventDate)").order("id", desc=True)
    if eventId is not None:
        q = q.eq("eventId", eventId)
    return q.execute().data


@app.post("/api/runners", status_code=201)
def create_runner(runner: Runner):
    result = supabase.table("runner").insert(runner.model_dump()).execute()
    return result.data[0]


@app.put("/api/runners/{runner_id}")
def update_runner(runner_id: int, runner: RunnerUpdate):
    updates = {k: v for k, v in runner.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = supabase.table("runner").update(updates).eq("id", runner_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Runner not found")
    return result.data[0]


@app.delete("/api/runners/{runner_id}", status_code=204)
def delete_runner(runner_id: int):
    result = supabase.table("runner").delete().eq("id", runner_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Runner not found")


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
