from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Mapping
from numbers import Real
from typing import Any

from insights_service.config import MIN_COHORT_SIZE


class Cohort:
    def __init__(self, feature_rows: Iterable[Mapping[str, Any]], min_size: int = MIN_COHORT_SIZE):
        values: dict[str, list[float]] = {}
        for row in feature_rows:
            for name, value in row.items():
                if isinstance(value, Real) and not isinstance(value, bool):
                    values.setdefault(name, []).append(float(value))

        self._sorted = {name: sorted(column) for name, column in values.items() if len(column) >= min_size}

    def share_below(self, feature_name: str, value: float) -> float | None:
        column = self._sorted.get(feature_name)
        if column is None:
            return None
        return bisect_left(column, value) / len(column)

    def share_above(self, feature_name: str, value: float) -> float | None:
        column = self._sorted.get(feature_name)
        if column is None:
            return None
        return (len(column) - bisect_right(column, value)) / len(column)
