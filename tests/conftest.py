from datetime import datetime, timedelta

import pytest

from app.config import CAMPUS_TIMEZONE
from app.database import connect
from app.main import create_app


@pytest.fixture
def app(tmp_path):
    application = create_app(str(tmp_path / "test.sqlite3"))
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def db(app):
    connection = connect(app.config["DATABASE"])
    yield connection
    connection.close()


@pytest.fixture
def client(app):
    return app.test_client()


def _login(app, username, password):
    test_client = app.test_client()
    response = test_client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.get_data(as_text=True)
    return test_client


@pytest.fixture
def student(app):
    return _login(app, "student_01", "123456")


@pytest.fixture
def advisor(app):
    return _login(app, "advisor_01", "123456")


@pytest.fixture
def manager(app):
    return _login(app, "manager_01", "123456")


@pytest.fixture
def admin(app):
    return _login(app, "admin", "admin123")


@pytest.fixture
def future_day():
    return (datetime.now(CAMPUS_TIMEZONE) + timedelta(days=10)).date().isoformat()


@pytest.fixture
def insert_reservation(db):
    def _insert(code, *, user_id=1, venue_id=1, day="2099-01-01", start="10:00", end="12:00",
                status="APPROVED", equip=None):
        db.execute(
            """INSERT INTO reservations(reservation_code, user_id, venue_id, title, activity_type,
               expected_attendance, reserve_date, start_time, end_time, description, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (code, user_id, venue_id, "测试活动", "学术讲座", 10, day, start, end, "", status,
             "2099-01-01 08:00:00", "2099-01-01 08:00:00"),
        )
        reservation_id = db.execute(
            "SELECT id FROM reservations WHERE reservation_code = ?", (code,)
        ).fetchone()["id"]
        for equipment_id, quantity in (equip or {}).items():
            db.execute(
                "INSERT INTO reservation_equipments(reservation_id, equipment_id, quantity) VALUES (?, ?, ?)",
                (reservation_id, equipment_id, quantity),
            )
        return reservation_id

    return _insert
