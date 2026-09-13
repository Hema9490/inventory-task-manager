"""
Domain classes (OOP layer).

Kept independent of Flask/sqlite3 so business rules are unit-testable
in isolation, and inheritance is used for the two task-like entities
that share behavior (Task, and a specialized RestockTask).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


class DomainError(Exception):
    """Raised when a business rule is violated."""


@dataclass
class Item:
    sku: str
    name: str
    category: str
    quantity: int = 0
    reorder_threshold: int = 5
    unit_price: float = 0.0
    id: Optional[int] = None

    def is_low_stock(self) -> bool:
        return self.quantity <= self.reorder_threshold

    def deduct(self, amount: int) -> None:
        if amount <= 0:
            raise DomainError("Deduction amount must be positive.")
        if amount > self.quantity:
            raise DomainError(
                f"Cannot deduct {amount} units; only {self.quantity} in stock."
            )
        self.quantity -= amount

    def restock(self, amount: int) -> None:
        if amount <= 0:
            raise DomainError("Restock amount must be positive.")
        self.quantity += amount


class WorkItem:
    """Base class for anything that can be prioritized and completed.

    Task and RestockTask both inherit from this so the priority queue
    (see priority_queue.py) can operate on either polymorphically.
    """

    VALID_STATUSES = ("open", "in-progress", "closed")

    def __init__(self, title: str, priority: int = 3, description: str = ""):
        if not (1 <= priority <= 5):
            raise DomainError("Priority must be between 1 (highest) and 5 (lowest).")
        self.title = title
        self.priority = priority
        self.description = description
        self.status = "open"
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None

    def start(self) -> None:
        if self.status != "open":
            raise DomainError(f"Cannot start a task with status '{self.status}'.")
        self.status = "in-progress"

    def complete(self) -> None:
        if self.status == "closed":
            raise DomainError("Task is already closed.")
        self.status = "closed"
        self.completed_at = datetime.now(timezone.utc)

    def __lt__(self, other: "WorkItem") -> bool:
        # Lower priority number = more urgent = "less than" for a min-heap.
        return self.priority < other.priority


class Task(WorkItem):
    """A general operational task, optionally linked to an inventory item."""

    def __init__(self, title: str, priority: int = 3, description: str = "",
                 related_item_id: Optional[int] = None):
        super().__init__(title, priority, description)
        self.related_item_id = related_item_id


class RestockTask(Task):
    """A task auto-generated when an item drops below its reorder threshold.

    Inherits Task's lifecycle but forces high urgency and carries the
    triggering item's shortfall so the queue naturally surfaces it first.
    """

    def __init__(self, item: Item, shortfall: int):
        if shortfall <= 0:
            raise DomainError("Shortfall must be positive to create a RestockTask.")
        priority = 1 if shortfall >= item.reorder_threshold else 2
        super().__init__(
            title=f"Restock {item.name} ({item.sku})",
            priority=priority,
            description=f"Quantity {item.quantity} is below threshold "
                         f"{item.reorder_threshold}; shortfall of {shortfall} units.",
            related_item_id=item.id,
        )
        self.shortfall = shortfall


@dataclass
class Order:
    item_id: int
    quantity: int
    order_type: str  # "sale" or "restock"
    id: Optional[int] = None

    def __post_init__(self):
        if self.order_type not in ("sale", "restock"):
            raise DomainError("order_type must be 'sale' or 'restock'.")
        if self.quantity <= 0:
            raise DomainError("Order quantity must be positive.")
