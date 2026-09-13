"""
Data Structures & Algorithms module: explicit search/sort routines used
for inventory lookup, instead of relying only on a database index.

These are intentionally hand-implemented (not just `sorted()` +
`in`) so the algorithmic complexity is visible: binary search is
O(log n) on a sorted list, merge sort is O(n log n) and stable.
"""

from typing import List, Optional, Sequence, TypeVar

from app.models import Item

T = TypeVar("T")


def binary_search_by_sku(items: Sequence[Item], target_sku: str) -> Optional[Item]:
    """Binary search for an Item by SKU.

    Precondition: `items` must already be sorted by `sku` ascending.
    Returns the matching Item, or None if not found. O(log n).
    """
    lo, hi = 0, len(items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        mid_sku = items[mid].sku
        if mid_sku == target_sku:
            return items[mid]
        if mid_sku < target_sku:
            lo = mid + 1
        else:
            hi = mid - 1
    return None


def merge_sort_items_by_quantity(items: List[Item]) -> List[Item]:
    """Stable merge sort of items by ascending quantity. O(n log n).

    Used for the low-stock view where a stable, predictable ordering
    matters more than raw speed on what is typically a small list.
    """
    if len(items) <= 1:
        return items[:]

    mid = len(items) // 2
    left = merge_sort_items_by_quantity(items[:mid])
    right = merge_sort_items_by_quantity(items[mid:])
    return _merge(left, right)


def _merge(left: List[Item], right: List[Item]) -> List[Item]:
    result: List[Item] = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i].quantity <= right[j].quantity:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result
