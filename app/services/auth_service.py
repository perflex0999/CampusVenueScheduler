from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from secrets import token_urlsafe
from typing import Any

from flask import g, session
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import get_db, transaction
from app.models import Role, append_audit
from app.schemas import ApiError, flag, now, password_value, text, timestamp

PASSWORD_METHOD = "pbkdf2:sha256:600000"
DUMMY_PASSWORD = generate_password_hash(token_urlsafe(), method=PASSWORD_METHOD)


def password_hash(password: str) -> str:
    return generate_password_hash(password, method=PASSWORD_METHOD)


def public_user(user: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": user["username"], "name": user["real_name"], "role": user["role"],
        "department": user["department"], "enabled": bool(user["is_active"]),
    }


def current_user() -> sqlite3.Row | None:
    if "user" not in g:
        g.user = None
        uid, version = session.get("uid"), session.get("version")
        if uid and version:
            user = get_db().execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (uid,)).fetchone()
            if user and user["auth_version"] == version:
                g.user = user
            else:
                session.clear()
    return g.user


def require_user(*roles: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def authorized(*args: Any, **kwargs: Any) -> Any:
            user = current_user()
            if user is None:
                raise ApiError("请先登录。", 401)
            if roles and user["role"] not in roles:
                raise ApiError("当前账号没有此操作权限。", 403)
            return view(*args, **kwargs)

        return authorized

    return decorator


def login(db: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    username = text(data, "username", "学号或工号", limit=32)
    password = data.get("password")
    if not isinstance(password, str) or not password or len(password) > 128:
        raise ApiError("请输入有效的密码。")
    current = now()
    time = current.isoformat(sep=" ")
    with transaction(db):
        attempt = db.execute("SELECT * FROM login_attempts WHERE username = ?", (username,)).fetchone()
        if attempt and attempt["lock_until"] and attempt["lock_until"] > time:
            raise ApiError("密码连续输错 5 次，账号暂时锁定，请在 5 分钟后重试。", 429)
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        valid = check_password_hash(user["password_hash"] if user else DUMMY_PASSWORD, password)
        if user and user["is_active"] and valid:
            db.execute("DELETE FROM login_attempts WHERE username = ?", (username,))
        else:
            failures = (attempt["failures"] if attempt and not attempt["lock_until"] else 0) + 1
            locked_until = (current + timedelta(minutes=5)).isoformat(sep=" ") if failures >= 5 else None
            db.execute(
                """INSERT INTO login_attempts(username, failures, lock_until, updated_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT(username) DO UPDATE SET failures = excluded.failures,
                   lock_until = excluded.lock_until, updated_at = excluded.updated_at""",
                (username, failures, locked_until, time),
            )
    if not (user and user["is_active"] and valid):
        if locked_until:
            raise ApiError("密码连续输错 5 次，账号已锁定 5 分钟。", 429)
        raise ApiError("账号或密码错误，或账号已停用。", 400)
    start_session(user["id"], user["auth_version"])
    return public_user(user)


def start_session(uid: int, version: str) -> None:
    session.clear()
    session.permanent = True
    session.update(uid=uid, version=version)


def update_profile(db: sqlite3.Connection, user: sqlite3.Row, data: dict[str, Any]) -> None:
    phone = text(data, "phone", "联系电话", required=False, limit=20)
    email = text(data, "email", "电子邮箱", required=False, limit=64)
    if email and (email.count("@") != 1 or any(char.isspace() for char in email) or not all(email.split("@"))):
        raise ApiError("请填写有效的电子邮箱。", field="email")
    with transaction(db):
        db.execute("UPDATE users SET phone = ?, email = ? WHERE id = ?", (phone, email, user["id"]))


def change_password(db: sqlite3.Connection, user: sqlite3.Row, data: dict[str, Any]) -> None:
    password = password_value(data)
    if password != data.get("confirm"):
        raise ApiError("两次输入的新密码不一致。", field="confirm")
    current = data.get("current")
    if not isinstance(current, str) or len(current) > 128 or not check_password_hash(user["password_hash"], current):
        raise ApiError("当前密码错误。", field="current")
    version = token_urlsafe()
    hashed = password_hash(password)
    with transaction(db):
        result = db.execute(
            "UPDATE users SET password_hash = ?, auth_version = ? WHERE id = ? AND auth_version = ?",
            (hashed, version, user["id"], user["auth_version"]),
        )
        if not result.rowcount:
            raise ApiError("账号信息已更新，请重新登录。", 401)
    start_session(user["id"], version)


def update_user(db: sqlite3.Connection, operator: sqlite3.Row, username: str, data: dict[str, Any]) -> None:
    role = text(data, "role", "角色")
    if role not in Role:
        raise ApiError("请选择有效角色。", field="role")
    enabled = flag(data, "enabled")
    password = password_value(data, required=False)
    with transaction(db):
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None:
            raise ApiError("账号不存在。", 404)
        if user["id"] == operator["id"] and (not enabled or role != Role.ADMIN):
            raise ApiError("不能停用当前管理员账号或变更其角色。")
        if password or role != user["role"] or enabled != bool(user["is_active"]):
            db.execute(
                "UPDATE users SET role = ?, is_active = ?, password_hash = ?, auth_version = ? WHERE id = ?",
                (role, enabled, password_hash(password) if password else user["password_hash"], token_urlsafe(), user["id"]),
            )
            if password:
                db.execute("DELETE FROM login_attempts WHERE username = ?", (username,))
            append_audit(db, "SAVE_USER", operator["id"], timestamp(), comment=username)
            if user["id"] == operator["id"]:
                changed = db.execute("SELECT auth_version FROM users WHERE id = ?", (user["id"],)).fetchone()
                start_session(user["id"], changed["auth_version"])
