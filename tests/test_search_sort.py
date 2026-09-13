from app.models import Item
from app.search_sort import binary_search_by_sku, merge_sort_items_by_quantity


def _items():
    return [
        Item(id=1, sku="A100", name="Bolt", category="hardware", quantity=50),
        Item(id=2, sku="B200", name="Nut", category="hardware", quantity=5),
        Item(id=3, sku="C300", name="Washer", category="hardware", quantity=20),
    ]


def test_binary_search_finds_existing_sku():
    items = _items()  # already sorted by sku
    result = binary_search_by_sku(items, "B200")
    assert result is not None
    assert result.name == "Nut"


def test_binary_search_returns_none_for_missing_sku():
    items = _items()
    assert binary_search_by_sku(items, "Z999") is None


def test_binary_search_on_empty_list():
    assert binary_search_by_sku([], "A100") is None


def test_merge_sort_orders_by_quantity_ascending():
    items = _items()
    sorted_items = merge_sort_items_by_quantity(items)
    quantities = [i.quantity for i in sorted_items]
    assert quantities == sorted(quantities)
    assert sorted_items[0].name == "Nut"
    assert sorted_items[-1].name == "Bolt"


def test_merge_sort_is_stable_for_equal_quantities():
    a = Item(id=1, sku="A", name="First", category="x", quantity=10)
    b = Item(id=2, sku="B", name="Second", category="x", quantity=10)
    result = merge_sort_items_by_quantity([a, b])
    assert [i.name for i in result] == ["First", "Second"]


def test_merge_sort_handles_empty_and_single():
    assert merge_sort_items_by_quantity([]) == []
    one = [Item(id=1, sku="A", name="Solo", category="x", quantity=1)]
    assert merge_sort_items_by_quantity(one) == one
