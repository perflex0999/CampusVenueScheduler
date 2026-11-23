from app.services.venue_service import overlapping_lock, overlapping_reservation


def test_half_open_back_to_back_not_conflicting(db, insert_reservation):
    insert_reservation("C1", start="10:00", end="12:00")
    assert overlapping_reservation(db, 1, "2099-01-01", "12:00", "14:00") is None


def test_true_overlap_conflicts(db, insert_reservation):
    insert_reservation("C2", start="10:00", end="12:00")
    row = overlapping_reservation(db, 1, "2099-01-01", "11:00", "13:00")
    assert row is not None
    assert row["title"] == "测试活动"


def test_exclude_skips_self(db, insert_reservation):
    reservation_id = insert_reservation("C3", start="10:00", end="12:00")
    assert overlapping_reservation(db, 1, "2099-01-01", "10:00", "12:00", exclude=reservation_id) is None


def test_pending_advisor_does_not_block(db, insert_reservation):
    insert_reservation("C4", start="10:00", end="12:00", status="PENDING_ADVISOR")
    assert overlapping_reservation(db, 1, "2099-01-01", "11:00", "13:00") is None


def test_lock_overlap(db):
    db.execute(
        "INSERT INTO venue_locks(venue_id, lock_date, start_time, end_time, reason, operator_id) VALUES (?, ?, ?, ?, ?, ?)",
        (1, "2099-01-01", "10:00", "12:00", "检修", 4),
    )
    assert overlapping_lock(db, 1, "2099-01-01", "11:00", "13:00") is not None
    assert overlapping_lock(db, 1, "2099-01-01", "12:00", "13:00") is None
