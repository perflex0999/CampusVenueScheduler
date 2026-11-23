from datetime import timedelta

from app.models import Role, Status
from app.schemas import now
from app.services.booking_service import can_cancel, can_review, reviewer_status


def test_reviewer_status_maps_role():
    assert reviewer_status({"role": Role.ADVISOR}) == Status.PENDING_ADVISOR
    assert reviewer_status({"role": Role.MANAGER}) == Status.PENDING_VENUE


def test_can_review_advisor_same_department():
    user = {"role": Role.ADVISOR, "department": "计算机学院"}
    row = {"status": Status.PENDING_ADVISOR, "department": "计算机学院"}
    assert can_review(user, row) is True


def test_can_review_advisor_other_department():
    user = {"role": Role.ADVISOR, "department": "计算机学院"}
    row = {"status": Status.PENDING_ADVISOR, "department": "外国语学院"}
    assert can_review(user, row) is False


def test_can_review_manager_ignores_department():
    user = {"role": Role.MANAGER, "department": "教务处"}
    row = {"status": Status.PENDING_VENUE, "department": "计算机学院"}
    assert can_review(user, row) is True


def test_can_review_advisor_requires_advisor_status():
    user = {"role": Role.ADVISOR, "department": "计算机学院"}
    row = {"status": Status.PENDING_VENUE, "department": "计算机学院"}
    assert can_review(user, row) is False


def test_can_cancel_owner_well_in_advance():
    start = now() + timedelta(days=1)
    user = {"id": 1, "role": Role.STUDENT}
    row = {"user_id": 1, "reserve_date": start.date().isoformat(), "start_time": "10:00", "status": Status.APPROVED}
    assert can_cancel(user, row) is True


def test_can_cancel_owner_inside_cutoff():
    start = now() + timedelta(hours=1)
    user = {"id": 1, "role": Role.STUDENT}
    row = {"user_id": 1, "reserve_date": start.date().isoformat(),
           "start_time": start.strftime("%H:%M"), "status": Status.APPROVED}
    assert can_cancel(user, row) is False


def test_can_cancel_manager_no_cutoff():
    start = now() + timedelta(hours=1)
    user = {"id": 4, "role": Role.MANAGER}
    row = {"user_id": 1, "reserve_date": start.date().isoformat(),
           "start_time": start.strftime("%H:%M"), "status": Status.APPROVED}
    assert can_cancel(user, row) is True
