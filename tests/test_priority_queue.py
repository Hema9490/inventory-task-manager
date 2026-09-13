import pytest

from app.priority_queue import PriorityQueue


def test_empty_queue():
    pq = PriorityQueue()
    assert pq.is_empty() is True
    assert len(pq) == 0
    assert pq.peek() is None


def test_pop_from_empty_raises():
    pq = PriorityQueue()
    with pytest.raises(IndexError):
        pq.pop()


def test_lower_priority_number_pops_first():
    pq = PriorityQueue()
    pq.push("low-urgency", priority=5)
    pq.push("high-urgency", priority=1)
    pq.push("mid-urgency", priority=3)

    assert pq.pop() == "high-urgency"
    assert pq.pop() == "mid-urgency"
    assert pq.pop() == "low-urgency"


def test_equal_priority_is_fifo_stable():
    pq = PriorityQueue()
    pq.push("first", priority=2)
    pq.push("second", priority=2)
    pq.push("third", priority=2)

    assert pq.pop() == "first"
    assert pq.pop() == "second"
    assert pq.pop() == "third"


def test_peek_does_not_remove():
    pq = PriorityQueue()
    pq.push("a", priority=1)
    assert pq.peek() == "a"
    assert len(pq) == 1


def test_to_sorted_list_is_non_destructive():
    pq = PriorityQueue()
    pq.push("b", priority=2)
    pq.push("a", priority=1)
    snapshot = pq.to_sorted_list()
    assert snapshot == ["a", "b"]
    assert len(pq) == 2  # unchanged
