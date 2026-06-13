from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from database import supabase

app = FastAPI()


class MenuItem(BaseModel):
    itemName: str
    itemCost: int
    itemType: str


class MenuItemUpdate(BaseModel):
    itemName: Optional[str] = None
    itemCost: Optional[int] = None
    itemType: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/menu.html") as f:
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
