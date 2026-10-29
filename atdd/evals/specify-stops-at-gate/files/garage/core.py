"""A parking garage: vehicles enter and leave; capacity is finite."""
from __future__ import annotations


class GarageFull(Exception):
    """Raised when a vehicle tries to enter a garage with no free spaces."""


class Garage:
    def __init__(self, capacity: int) -> None:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        self._capacity = capacity
        self._present: set[str] = set()

    def free_spaces(self) -> int:
        return self._capacity - len(self._present)

    def enter(self, plate: str) -> None:
        if plate in self._present:
            return
        if self.free_spaces() == 0:
            raise GarageFull(f"garage full: {plate} cannot enter")
        self._present.add(plate)

    def leave(self, plate: str) -> None:
        self._present.discard(plate)

    def is_present(self, plate: str) -> bool:
        return plate in self._present
