"""Count matches without downloading them.

``resultType=hits`` always returns 0 on this service, so counting probes with
single-feature requests: "is there a feature at start index N?". The probe
function is injected so the logic can be tested without a network.
"""
from dataclasses import dataclass
from typing import Callable

from .query import WFS_PAGING_LIMIT


class CancelledError(Exception):
    """The user cancelled or changed the search while a request series was running."""


# ``exists(index)`` is True when a request with startIndex=index returns a feature.
Probe = Callable[[int], bool]


@dataclass(frozen=True)
class Count:
    value: int
    exact: bool  # False when ``value`` is a lower bound (limit reached)


def unknown_names(names, name_exists) -> tuple:
    """The names for which ``name_exists(name)`` is False, for example misspelled ones."""
    return tuple(name for name in names if not name_exists(name))


def at_least(exists: Probe, threshold: int) -> bool:
    """True when the result holds at least ``threshold`` features. One request."""
    return exists(threshold - 1)


def count(exists: Probe, limit: int = WFS_PAGING_LIMIT) -> Count:
    """Exact count by doubling and bisection: about 2 * log2(n) requests.

    A result at or above ``limit`` is recognised with two requests, so a search that
    matches almost everything does not cost dozens. Paging data can shift between
    requests, so treat the result as approximate.
    """
    if not exists(0):
        return Count(0, True)
    if exists(limit - 1):
        return Count(limit, False)
    low, high = 1, 2  # exists(low - 1) is True, exists(limit - 1) is False
    while high <= limit and exists(high - 1):
        low, high = high, high * 2
    high = min(high, limit)
    while high - low > 1:
        mid = (low + high) // 2
        if exists(mid - 1):
            low = mid
        else:
            high = mid
    return Count(low, True)
