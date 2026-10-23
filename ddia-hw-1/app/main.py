import itertools
import os
import random
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from golden_signals import instrument

FAULT_RATE = float(os.environ.get("FAULT_RATE", "0"))


class OrderLine(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=1000)


class OrderIn(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    items: list[OrderLine] = Field(min_length=1, max_length=100)
    status: Literal["created", "paid", "shipped", "cancelled"] = "created"


class Order(OrderIn):
    id: int


def inject_fault() -> None:
    if random.random() < FAULT_RATE:
        raise HTTPException(503, "injected fault")


orders: dict[int, Order] = {}
next_id = itertools.count(1)
app = FastAPI()
with_faults = [Depends(inject_fault)]


def find(order_id: int) -> Order:
    if order_id not in orders:
        raise HTTPException(404, "order not found")
    return orders[order_id]


@app.post("/orders", status_code=201, dependencies=with_faults)
async def create_order(body: OrderIn) -> Order:
    order = Order(id=next(next_id), **body.model_dump())
    orders[order.id] = order
    return order


@app.get("/orders", dependencies=with_faults)
async def list_orders(limit: int = Query(50, ge=1, le=500)) -> list[Order]:
    return list(itertools.islice(orders.values(), limit))


@app.get("/orders/{order_id}", dependencies=with_faults)
async def get_order(order_id: int) -> Order:
    return find(order_id)


@app.put("/orders/{order_id}", dependencies=with_faults)
async def replace_order(order_id: int, body: OrderIn) -> Order:
    find(order_id)
    orders[order_id] = Order(id=order_id, **body.model_dump())
    return orders[order_id]


instrument(app)


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}
