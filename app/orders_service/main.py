import random

from fastapi import Depends, FastAPI, HTTPException, Query
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from orders_service.settings import load_settings
from orders_service.storage import InMemoryOrderStorage, Order, OrderLine, OrderNotFound, OrderStatus

settings = load_settings()
storage = InMemoryOrderStorage()
app = FastAPI(title=settings.deployment_name)
app.mount("/metrics", make_asgi_app())


class OrderLineDto(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=1000)


class OrderCreateIn(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    items: list[OrderLineDto] = Field(min_length=1, max_length=100)


class OrderReplaceIn(OrderCreateIn):
    status: OrderStatus


class OrderOut(BaseModel):
    id: int
    customer_id: str
    items: list[OrderLineDto]
    status: OrderStatus


def to_lines(items: list[OrderLineDto]) -> tuple[OrderLine, ...]:
    return tuple(OrderLine(sku=item.sku, quantity=item.quantity) for item in items)


def to_out(order: Order) -> OrderOut:
    items = [OrderLineDto(sku=line.sku, quantity=line.quantity) for line in order.lines]
    return OrderOut(id=order.id, customer_id=order.customer_id, items=items, status=order.status)


def inject_fault() -> None:
    if random.random() < settings.fault_rate:
        raise HTTPException(status_code=503, detail="injected fault")


def order_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="order not found")


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok", "pod": settings.pod_id, "datacenter": settings.datacenter}


@app.post("/orders", status_code=201, dependencies=[Depends(inject_fault)])
async def create_order(body: OrderCreateIn) -> OrderOut:
    order = storage.create(body.customer_id, to_lines(body.items))
    return to_out(order)


@app.get("/orders", dependencies=[Depends(inject_fault)])
async def list_orders(limit: int = Query(default=50, ge=1, le=500)) -> list[OrderOut]:
    return [to_out(order) for order in storage.list(limit)]


@app.get("/orders/{order_id}", dependencies=[Depends(inject_fault)])
async def get_order(order_id: int) -> OrderOut:
    try:
        order = storage.get(order_id)
    except OrderNotFound:
        raise order_not_found()
    return to_out(order)


@app.put("/orders/{order_id}", dependencies=[Depends(inject_fault)])
async def replace_order(order_id: int, body: OrderReplaceIn) -> OrderOut:
    try:
        order = storage.replace(order_id, body.customer_id, to_lines(body.items), body.status)
    except OrderNotFound:
        raise order_not_found()
    return to_out(order)
