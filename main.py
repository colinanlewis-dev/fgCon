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


@app.post("/api/events", status_code=201)
def create_event(event: Event):
    result = supabase.table("event").insert(event.model_dump()).execute()
    return result.data[0]


@app.put("/api/events/{event_id}")
def update_event(event_id: int, event: EventUpdate):
    updates = {k: v for k, v in event.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = supabase.table("event").update(updates).eq("id", event_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Event not found")
    return result.data[0]


@app.delete("/api/events/{event_id}", status_code=204)
def delete_event(event_id: int):
    result = supabase.table("event").delete().eq("id", event_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Event not found")
