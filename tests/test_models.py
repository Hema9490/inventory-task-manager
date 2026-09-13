import pytest

from app.models import DomainError, Item, Task, RestockTask, Order


def test_item_deduct_reduces_quantity():
    item = Item(sku="SKU1", name="Widget", category="tools", quantity=10)
    item.deduct(3)
    assert item.quantity == 7


def test_item_deduct_raises_when_insufficient_stock():
    item = Item(sku="SKU1", name="Widget", category="tools", quantity=2)
    with pytest.raises(DomainError):
        item.deduct(5)


def test_item_deduct_rejects_non_positive_amount():
    item = Item(sku="SKU1", name="Widget", category="tools", quantity=5)
    with pytest.raises(DomainError):
        item.deduct(0)


def test_item_restock_increases_quantity():
    item = Item(sku="SKU1", name="Widget", category="tools", quantity=2)
    item.restock(8)
    assert item.quantity == 10


def test_item_is_low_stock():
    item = Item(sku="SKU1", name="Widget", category="tools", quantity=2, reorder_threshold=5)
    assert item.is_low_stock() is True
    item.restock(10)
    assert item.is_low_stock() is False


def test_task_lifecycle_start_then_complete():
    task = Task(title="Fix bug", priority=2)
    assert task.status == "open"
    task.start()
    assert task.status == "in-progress"
    task.complete()
    assert task.status == "closed"
    assert task.completed_at is not None


def test_task_cannot_start_twice():
    task = Task(title="Fix bug", priority=2)
    task.start()
    with pytest.raises(DomainError):
        task.start()


def test_task_cannot_complete_twice():
    task = Task(title="Fix bug", priority=2)
    task.complete()
    with pytest.raises(DomainError):
        task.complete()


def test_task_rejects_invalid_priority():
    with pytest.raises(DomainError):
        Task(title="Bad", priority=0)
    with pytest.raises(DomainError):
        Task(title="Bad", priority=6)


def test_task_ordering_by_priority():
    high = Task(title="Urgent", priority=1)
    low = Task(title="Later", priority=5)
    assert high < low


def test_restock_task_priority_reflects_shortfall():
    item = Item(sku="SKU1", name="Widget", category="tools", quantity=1, reorder_threshold=5)
    severe = RestockTask(item=item, shortfall=5)
    mild = RestockTask(item=item, shortfall=1)
    assert severe.priority == 1
    assert mild.priority == 2


def test_restock_task_rejects_non_positive_shortfall():
    item = Item(sku="SKU1", name="Widget", category="tools", quantity=1, reorder_threshold=5)
    with pytest.raises(DomainError):
        RestockTask(item=item, shortfall=0)


def test_order_rejects_invalid_type():
    with pytest.raises(DomainError):
        Order(item_id=1, quantity=5, order_type="invalid")


def test_order_rejects_non_positive_quantity():
    with pytest.raises(DomainError):
        Order(item_id=1, quantity=0, order_type="sale")
