from typing import TypeVar, Iterator

T = TypeVar("T")


def chunked(items: list[T], size: int) -> Iterator[list[T]]:
    for i in range(0, len(items), size):
        yield items[i:i + size]