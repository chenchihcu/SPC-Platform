from typing import Any, List


class InMemoryRepository:
    def __init__(self) -> None:
        self.items: List[Any] = []

    def add(self, item: Any) -> None:
        """Add an item to the repository."""
        self.items.append(item)

    def list_all(self) -> List[Any]:
        """Return all items in the repository."""
        return list(self.items)
