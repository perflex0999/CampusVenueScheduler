import pytest

from app.schemas import ApiError
from app.services.equipment_service import available_quantities, validate_items


def test_available_quantities_counts_only_approved(db, insert_reservation):
    insert_reservation("E1", start="10:00", end="12:00", status="APPROVED", equip={1: 2})
    insert_reservation("E2", start="10:30", end="11:30", status="PENDING_VENUE", equip={1: 5})
    occupied = available_quantities(db, "2099-01-01", "09:00", "12:30")
    assert occupied[1] == 2


def test_validate_items_rejects_over_max_per_booking(db):
    with pytest.raises(ApiError):
        validate_items(db, {"EQ-001": 6}, ("2099-01-01", "10:00", "12:00"))


def test_validate_items_draft_skips_availability(db):
    result = validate_items(db, {"EQ-001": 100}, ("2099-01-01", "10:00", "12:00"), draft=True)
    assert result == [(1, 100)]


def test_validate_items_rejects_inactive_equipment(db):
    db.execute("UPDATE equipments SET is_active = 0 WHERE id = 1")
    with pytest.raises(ApiError):
        validate_items(db, {"EQ-001": 1}, ("2099-01-01", "10:00", "12:00"))
