"""Executable specifications for Story 7: drivers can reserve a space."""
from tests.acceptance.support.garage_dsl import Lot


def test_driver_reserves_a_space_when_one_is_free() -> None:
    lot = Lot(free_spaces=2)
    lot.driver("ana").reserves_a_space()
    lot.confirm_free_spaces(1)


def test_reservation_is_refused_when_garage_is_full() -> None:
    lot = Lot(free_spaces=0)
    lot.driver("ana").reserves_a_space()
    lot.driver("ana").confirm_reservation_refused("garage full")
    lot.confirm_free_spaces(0)


def test_cancelling_a_reservation_frees_the_space() -> None:
    lot = Lot(free_spaces=1)
    lot.driver("ana").reserves_a_space()
    lot.driver("ana").cancels_reservation()
    lot.confirm_free_spaces(1)
