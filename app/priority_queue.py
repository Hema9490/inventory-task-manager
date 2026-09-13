"""
Data Structures module: a small binary-heap-backed priority queue.

Built on top of heapq rather than a third-party scheduler library, so
the underlying structure (array-backed binary heap, O(log n) push/pop)
is visible and testable — this is the DSA piece of the project, kept
explicit rather than hidden inside a framework.
"""

import heapq
import itertools
from typing import Generic, List, Optional, Tuple, TypeVar

T = TypeVar("T")


class PriorityQueue(Generic[T]):
    """Min-priority queue: lower `priority` value = popped first.

    Uses an insertion counter as a tiebreaker so items with equal
    priority are returned in FIFO order (stable ordering), and so the
    heap never needs to compare the payload objects directly.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[int, int, T]] = []
        self._counter = itertools.count()

    def push(self, item: T, priority: int) -> None:
        count = next(self._counter)
        heapq.heappush(self._heap, (priority, count, item))

    def pop(self) -> T:
        if not self._heap:
            raise IndexError("pop from an empty PriorityQueue")
        _, _, item = heapq.heappop(self._heap)
        return item

    def peek(self) -> Optional[T]:
        if not self._heap:
            return None
        return self._heap[0][2]

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def to_sorted_list(self) -> List[T]:
        """Non-destructive snapshot in priority order (for API responses)."""
        return [item for _, _, item in sorted(self._heap)]
