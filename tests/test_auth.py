def test_login_success(client):
    response = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    assert response.get_json()["role"] == "admin"


def test_login_wrong_password(client):
    response = client.post("/api/auth/login", json={"username": "student_01", "password": "wrong"})
    assert response.status_code == 400


def test_login_lockout_after_five_failures(client):
    for _ in range(4):
        assert client.post("/api/auth/login", json={"username": "student_01", "password": "wrong"}).status_code == 400
    assert client.post("/api/auth/login", json={"username": "student_01", "password": "wrong"}).status_code == 429


def test_auth_version_change_invalidates_session(student, admin):
    assert student.get("/api/workspace").status_code == 200
    assert admin.patch(
        "/api/admin/users/student_01",
        json={"role": "student", "enabled": True, "password": "newpass456"},
    ).status_code == 200
    assert student.get("/api/workspace").status_code == 401
