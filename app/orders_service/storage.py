import itertools
from dataclasses import dataclass
from enum import StrEnum


class OrderStatus(StrEnum):
    CREATED = "created"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class OrderLine:
    sku: str
    quantity: int


@dataclass(frozen=True)
class Order:
    id: int
    customer_id: str
    lines: tuple[OrderLine, ...]
    status: OrderStatus


class OrderNotFound(Exception):
    pass


class InMemoryOrderStorage:
    def __init__(self) -> None:
        self._orders: dict[int, Order] = {}
        self._ids = itertools.count(1)

    def create(self, customer_id: str, lines: tuple[OrderLine, ...]) -> Order:
        order = Order(id=next(self._ids), customer_id=customer_id, lines=lines, status=OrderStatus.CREATED)
        self._orders[order.id] = order
        return order

    def get(self, order_id: int) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFound(order_id)
        return order

    def list(self, limit: int) -> list[Order]:
        return list(itertools.islice(self._orders.values(), limit))

    def replace(self, order_id: int, customer_id: str, lines: tuple[OrderLine, ...], status: OrderStatus) -> Order:
        if order_id not in self._orders:
            raise OrderNotFound(order_id)
        order = Order(id=order_id, customer_id=customer_id, lines=lines, status=status)
        self._orders[order_id] = order
        return order
