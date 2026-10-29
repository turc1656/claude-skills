import pytest

from garage import Garage, GarageFull


def test_vehicle_entering_takes_a_space() -> None:
    garage = Garage(capacity=2)
    garage.enter("ABC-123")
    assert garage.free_spaces() == 1


def test_full_garage_refuses_entry() -> None:
    garage = Garage(capacity=1)
    garage.enter("ABC-123")
    with pytest.raises(GarageFull):
        garage.enter("XYZ-999")


def test_leaving_frees_the_space() -> None:
    garage = Garage(capacity=1)
    garage.enter("ABC-123")
    garage.leave("ABC-123")
    assert garage.free_spaces() == 1
