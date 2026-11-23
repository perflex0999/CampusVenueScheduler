def _booking_payload(future_day, **overrides):
    payload = {
        "title": "管理流测试活动", "type": "学术讲座", "people": 20,
        "venue": "ZJ-101", "date": future_day, "start": "14:00", "end": "16:00",
        "description": "用于管理流集成测试。", "equipment": {},
    }
    payload.update(overrides)
    return payload


def test_venue_crud(manager):
    added = manager.post("/api/venues", json={
        "id": "TEST-01", "name": "测试场地", "building": "测试楼", "capacity": 50,
        "type": "会议室", "setup": "白板", "open": "08:00", "close": "21:00", "maintenance": False,
    })
    assert added.status_code == 201

    edited = manager.patch("/api/venues/TEST-01", json={
        "name": "测试场地改", "building": "测试楼", "capacity": 60,
        "type": "会议室", "setup": "白板投影", "open": "08:00", "close": "21:30", "maintenance": False,
    })
    assert edited.status_code == 200

    listed = manager.get("/api/venues")
    assert listed.status_code == 200
    assert listed.get_json()["total"] >= 13

    filtered = manager.get("/api/venues?q=测试")
    assert filtered.status_code == 200
    assert filtered.get_json()["total"] == 1


def test_venue_lock_flow(manager, db, future_day):
    added = manager.post("/api/venue-locks", json={
        "venue": "ZJ-101", "date": future_day, "start": "08:00", "end": "09:00", "reason": "测试锁定",
    })
    assert added.status_code == 201

    lock_id = db.execute("SELECT id FROM venue_locks WHERE reason = '测试锁定'").fetchone()["id"]
    removed = manager.delete(f"/api/venue-locks/{lock_id}", json={})
    assert removed.status_code == 200


def test_equipment_crud(manager):
    added = manager.post("/api/equipments", json={
        "id": "EQ-TEST", "name": "测试物资", "total": 5, "limit": 2, "unit": "个", "enabled": True,
    })
    assert added.status_code == 201

    edited = manager.patch("/api/equipments/EQ-TEST", json={
        "name": "测试物资改", "total": 8, "limit": 3, "unit": "个", "enabled": True,
    })
    assert edited.status_code == 200


def test_draft_lifecycle(student, future_day):
    draft = student.post("/api/reservations", json={
        "title": "草稿活动", "type": "学术讲座", "venue": "ZJ-101",
        "date": future_day, "start": "14:00", "end": "16:00", "description": "", "equipment": {}, "draft": True,
    })
    assert draft.status_code == 201
    reservation_id = draft.get_json()["id"]
    assert draft.get_json()["status"] == "DRAFT"

    edited = student.patch(f"/api/reservations/{reservation_id}", json={
        "title": "草稿活动改", "type": "学术讲座", "venue": "ZJ-101",
        "date": future_day, "start": "14:00", "end": "16:00", "description": "", "equipment": {}, "draft": True,
    })
    assert edited.status_code == 200

    deleted = student.delete(f"/api/reservations/{reservation_id}", json={})
    assert deleted.status_code == 200


def test_cancel_reservation(student, future_day):
    reservation_id = student.post("/api/reservations", json=_booking_payload(future_day)).get_json()["id"]
    assert student.post(f"/api/reservations/{reservation_id}/cancel", json={}).status_code == 200


def test_reject_flow(student, advisor, future_day):
    reservation_id = student.post("/api/reservations", json=_booking_payload(future_day)).get_json()["id"]
    response = advisor.post(f"/api/approvals/{reservation_id}/audit", json={"decision": "REJECTED", "comment": "方案不完整，请补充。"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "REJECTED"


def test_reschedule(student, advisor, manager, future_day):
    reservation_id = student.post("/api/reservations", json=_booking_payload(future_day)).get_json()["id"]
    advisor.post(f"/api/approvals/{reservation_id}/audit", json={"decision": "APPROVED", "comment": "同意。"})
    manager.post(f"/api/approvals/{reservation_id}/audit", json={"decision": "APPROVED", "comment": "批准。"})

    response = manager.patch(f"/api/reservations/{reservation_id}/schedule", json={
        "venue": "ZJ-101", "date": future_day, "start": "15:00", "end": "17:00", "comment": "调整时间",
    })
    assert response.status_code == 200


def test_profile_and_password(student):
    assert student.patch("/api/auth/profile", json={"phone": "13800000000", "email": "a@b.com"}).status_code == 200
    assert student.patch("/api/auth/password", json={
        "password": "newpass123", "confirm": "newpass123", "current": "123456",
    }).status_code == 200


def test_audit_and_pending(admin, advisor, student, future_day):
    student.post("/api/reservations", json=_booking_payload(future_day))
    assert advisor.get("/api/approvals/pending").status_code == 200
    assert admin.get("/api/admin/audit").status_code == 200


def test_venue_schedule_and_detail(student, future_day):
    assert student.get("/api/venues/ZJ-101").status_code == 200
    assert student.get(f"/api/venues/ZJ-101/schedule?date={future_day}").status_code == 200
