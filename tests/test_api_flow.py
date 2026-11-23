from datetime import timedelta

from app.main import create_app
from app.schemas import now


def _booking_payload(future_day, **overrides):
    payload = {
        "title": "集成测试活动", "type": "学术讲座", "people": 20,
        "venue": "ZJ-101", "date": future_day, "start": "14:00", "end": "16:00",
        "description": "用于集成测试的活动说明。", "equipment": {},
    }
    payload.update(overrides)
    return payload


def test_full_approval_flow(student, advisor, manager, future_day):
    created = student.post("/api/reservations", json=_booking_payload(future_day))
    assert created.status_code == 201
    reservation_id = created.get_json()["id"]
    assert created.get_json()["status"] == "PENDING_ADVISOR"

    first = advisor.post(f"/api/approvals/{reservation_id}/audit", json={"decision": "APPROVED", "comment": "同意举办。"})
    assert first.status_code == 200
    assert first.get_json()["status"] == "PENDING_VENUE"

    final = manager.post(f"/api/approvals/{reservation_id}/audit", json={"decision": "APPROVED", "comment": "场地已确认。"})
    assert final.status_code == 200
    assert final.get_json()["status"] == "APPROVED"


def test_overlapping_pending_venue_rejected(student, advisor, future_day):
    reservation_id = student.post("/api/reservations", json=_booking_payload(future_day)).get_json()["id"]
    advisor.post(f"/api/approvals/{reservation_id}/audit", json={"decision": "APPROVED", "comment": "同意。"})

    duplicate = student.post("/api/reservations", json=_booking_payload(future_day, title="冲突活动"))
    assert duplicate.status_code == 409


def test_student_cannot_review(student, future_day):
    reservation_id = student.post("/api/reservations", json=_booking_payload(future_day)).get_json()["id"]
    response = student.post(f"/api/approvals/{reservation_id}/audit", json={"decision": "APPROVED"})
    assert response.status_code == 403


def test_rejected_requires_reason(student, advisor, future_day):
    reservation_id = student.post("/api/reservations", json=_booking_payload(future_day)).get_json()["id"]
    response = advisor.post(f"/api/approvals/{reservation_id}/audit", json={"decision": "REJECTED", "comment": "太短"})
    assert response.status_code == 400


def test_finish_expired_archives_past_approved(manager, db, insert_reservation):
    past = now() - timedelta(days=1)
    insert_reservation("FINISH-ME", day=past.date().isoformat(), start="08:00", end="09:00", status="APPROVED")

    response = manager.get("/api/workspace")
    assert response.status_code == 200

    row = db.execute("SELECT status FROM reservations WHERE reservation_code = 'FINISH-ME'").fetchone()
    assert row["status"] == "FINISHED"


def test_unexpected_error_returns_json(tmp_path):
    application = create_app(str(tmp_path / "boom.sqlite3"))
    application.config.update(TESTING=False, PROPAGATE_EXCEPTIONS=False)

    @application.get("/boom")
    def boom():
        raise RuntimeError("boom")

    response = application.test_client().get("/boom")
    assert response.status_code == 500
    assert response.get_json()["message"] == "服务器内部错误，请稍后重试。"
