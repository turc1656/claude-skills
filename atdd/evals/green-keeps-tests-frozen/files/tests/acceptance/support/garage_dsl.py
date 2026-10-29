"""Domain layer and driver for the reservation specifications (one module: one feature, one protocol)."""
from __future__ import annotations

import uuid

from garage import Garage, GarageFull


def alias(name: str) -> str:
    """Functional isolation: 'ana' becomes 'ana-3f9c' so tests never share a plate."""
    return f"{name}-{uuid.uuid4().hex[:4]}"


class Lot:
    """The story's vocabulary: a lot with free spaces, drivers, reservations."""

    def __init__(self, free_spaces: int) -> None:
        self._garage = Garage(capacity=free_spaces)
        self._drivers: dict[str, Driver] = {}

    def driver(self, name: str) -> "Driver":
        if name not in self._drivers:
            self._drivers[name] = Driver(self._garage, alias(name))
        return self._drivers[name]

    def confirm_free_spaces(self, expected: int) -> None:
        actual = self._garage.free_spaces()
        assert actual == expected, f"free spaces is {actual}, expected {expected}"


class Driver:
    def __init__(self, garage: Garage, plate: str) -> None:
        self._garage, self._plate = garage, plate
        self._refusal: str | None = None

    def reserves_a_space(self) -> None:
        try:
            self._garage.reserve(self._plate)
        except GarageFull as refusal:
            self._refusal = str(refusal)

    def cancels_reservation(self) -> None:
        self._garage.cancel_reservation(self._plate)

    def confirm_reservation_refused(self, reason: str) -> None:
        assert self._refusal is not None, "the reservation was not refused"
        assert reason in self._refusal, f"refusal said {self._refusal!r}, expected it to mention {reason!r}"
