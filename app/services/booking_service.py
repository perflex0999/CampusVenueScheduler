from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from app.database import transaction
from app.models import AUDIT_LABELS, PENDING, Role, Status, append_audit
from app.schemas import ApiError, booking_input, now, period, text, timestamp
from app.services.equipment_service import validate_items
from app.services.venue_service import find_venue, overlapping_lock, overlapping_reservation

RESERVATION_QUERY = """
SELECT r.*, v.venue_code, u.username, u.real_name, u.department
FROM reservations r JOIN venues v ON v.id = r.venue_id JOIN users u ON u.id = r.user_id
"""


def find_reservation(db: sqlite3.Connection, reservation_id: int) -> sqlite3.Row:
    row = db.execute(RESERVATION_QUERY + " WHERE r.id = ?", (reservation_id,)).fetchone()
    if row is None:
        raise ApiError("申请单不存在。", 404)
    return row


def reviewer_status(user: sqlite3.Row) -> Status:
    return Status.PENDING_ADVISOR if user["role"] == Role.ADVISOR else Status.PENDING_VENUE


def can_review(user: sqlite3.Row, row: sqlite3.Row) -> bool:
    return (
        user["role"] in (Role.ADVISOR, Role.MANAGER) and row["status"] == reviewer_status(user)
        and (user["role"] == Role.MANAGER or user["department"] == row["department"])
    )


def can_cancel(user: sqlite3.Row, row: sqlite3.Row) -> bool:
    if row["user_id"] != user["id"] and user["role"] not in (Role.MANAGER, Role.ADMIN):
        return False
    starts = start_datetime(row)
    current = now()
    cutoff = timedelta(hours=2) if row["user_id"] == user["id"] else timedelta(0)
    return row["status"] in (*PENDING, Status.APPROVED) and starts > current and starts - current >= cutoff


def start_datetime(row: sqlite3.Row) -> datetime:
    return datetime.fromisoformat(f"{row['reserve_date']}T{row['start_time']}")


def audit_view(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "action": row["action"], "title": AUDIT_LABELS[row["action"]], "by": row["real_name"],
        "at": row["created_at"], "comment": row["comment"], "code": row["reservation_code"],
    }


def audit_entries(db: sqlite3.Connection, reservation_id: int | None = None) -> list[dict[str, Any]]:
    sql = "SELECT a.*, u.real_name FROM audit_logs a JOIN users u ON a.operator_id = u.id"
    if reservation_id is None:
        return [audit_view(row) for row in db.execute(sql + " ORDER BY a.created_at DESC, a.id DESC")]
    return [audit_view(row) for row in db.execute(sql + " WHERE a.reservation_id = ? ORDER BY a.id", (reservation_id,))]


def equipment_for(db: sqlite3.Connection, reservation_id: int) -> dict[str, int]:
    return {row["equipment_code"]: row["quantity"] for row in db.execute(
        """SELECT e.equipment_code, re.quantity FROM reservation_equipments re
           JOIN equipments e ON e.id = re.equipment_id WHERE re.reservation_id = ?""", (reservation_id,),
    )}


def reservation_view(db: sqlite3.Connection, row: sqlite3.Row, user: sqlite3.Row, *, detailed: bool = False) -> dict[str, Any]:
    result = {
        "id": row["id"], "code": row["reservation_code"], "venue": row["venue_code"],
        "title": row["title"], "date": row["reserve_date"], "start": row["start_time"], "end": row["end_time"],
        "status": row["status"], "detailed": detailed,
        "canCancel": can_cancel(user, row),
        "canReschedule": user["role"] == Role.MANAGER and row["status"] == Status.APPROVED and start_datetime(row) > now(),
    }
    if detailed:
        equipment = equipment_for(db, row["id"])
        result.update(
            user=row["username"], applicant=row["real_name"], created=row["created_at"],
            type=row["activity_type"], people=row["expected_attendance"], description=row["description"],
            equipment=equipment, history=audit_entries(db, row["id"]), rejectReason=row["reject_reason"],
        )
        if can_review(user, row):
            try:
                validate_slot(db, find_venue(db, row["venue_code"]), row["reserve_date"],
                              row["start_time"], row["end_time"], row["expected_attendance"], row["id"])
                validate_items(db, equipment, (row["reserve_date"], row["start_time"], row["end_time"]))
            except ApiError as error:
                result["reviewIssue"] = str(error)
    return result


def list_own(db: sqlite3.Connection, user: sqlite3.Row) -> list[dict[str, Any]]:
    rows = db.execute(RESERVATION_QUERY + " WHERE r.user_id = ? ORDER BY r.created_at DESC, r.id DESC", (user["id"],))
    return [reservation_view(db, row, user, detailed=True) for row in rows]


def list_pending(db: sqlite3.Connection, user: sqlite3.Row, sort: str = "created") -> list[dict[str, Any]]:
    order = "r.reserve_date, r.start_time, r.id" if sort == "date" else "r.created_at DESC, r.id DESC"
    rows = db.execute(
        RESERVATION_QUERY + " WHERE r.status = ? AND (? OR u.department = ?) ORDER BY " + order,
        (reviewer_status(user), user["role"] == Role.MANAGER, user["department"]),
    )
    return [reservation_view(db, row, user, detailed=True) for row in rows]


def list_schedule(db: sqlite3.Connection, user: sqlite3.Row, venue_id: int | None = None, day: str | None = None) -> list[dict[str, Any]]:
    rows = db.execute(
        RESERVATION_QUERY + """
        WHERE r.status IN (?, ?, ?) AND (? IS NULL OR r.venue_id = ?) AND (? IS NULL OR r.reserve_date = ?)
        ORDER BY r.start_time, r.id
        """,
        (Status.APPROVED, Status.PENDING_VENUE, Status.FINISHED, venue_id, venue_id, day, day),
    )
    return [reservation_view(db, row, user) for row in rows]


def validate_slot(db: sqlite3.Connection, venue: sqlite3.Row, day: str, start: str, end: str,
                  people: int, exclude: int | None = None) -> None:
    if venue["status"] != "AVAILABLE":
        raise ApiError("该场地处于维护状态，请选择其他场地。", 409, field="venue")
    if people > venue["capacity"]:
        raise ApiError(f"参加人数超过场地容量（{venue['capacity']} 人）。", field="people")
    if f"{day} {start}:00" <= timestamp():
        raise ApiError("请选择晚于当前时间的使用时段。", field="date")
    if start < venue["open_start"] or end > venue["open_end"]:
        raise ApiError(f"使用时段须在场地开放时间 {venue['open_start']}–{venue['open_end']} 内。", field="start")
    conflict = (overlapping_reservation(db, venue["id"], day, start, end, exclude)
                or overlapping_lock(db, venue["id"], day, start, end))
    if conflict:
        raise ApiError(f"时段冲突：{conflict['title']}（{conflict['start_time']}–{conflict['end_time']}）。", 409)


def save_reservation(db: sqlite3.Connection, user: sqlite3.Row, data: dict[str, Any],
                     reservation_id: int | None = None) -> dict[str, Any]:
    draft = data.get("draft", False)
    if type(draft) is not bool:
        raise ApiError("申请操作不正确。")
    values = booking_input(data, draft=draft)
    day, start, end = values["date"], values["start"], values["end"]
    with transaction(db):
        if reservation_id is not None:
            existing = find_reservation(db, reservation_id)
            if existing["user_id"] != user["id"]:
                raise ApiError("无权修改此申请。", 403)
            if existing["status"] not in (Status.DRAFT, Status.REJECTED):
                raise ApiError("只有草稿和已驳回的申请可修改。", 409)
        venue = find_venue(db, values["venue"])
        if not draft:
            validate_slot(db, venue, day, start, end, values["people"], reservation_id)
        equipment = validate_items(db, values["equipment"], (day, start, end), draft=draft)
        current = timestamp()
        status = Status.DRAFT if draft else Status.PENDING_ADVISOR
        fields = (venue["id"], values["title"], values["type"], values["people"], day, start, end,
                  values["description"], status)
        if reservation_id is None:
            reservation_id = db.execute(
                """INSERT INTO reservations(reservation_code, user_id, venue_id, title, activity_type,
                   expected_attendance, reserve_date, start_time, end_time, description, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (uuid4().hex, user["id"], *fields, current, current),
            ).lastrowid
            code = f"RES-{current[:10].replace('-', '')}-{reservation_id:03d}"
            db.execute("UPDATE reservations SET reservation_code = ? WHERE id = ?", (code, reservation_id))
        else:
            db.execute(
                """UPDATE reservations SET venue_id = ?, title = ?, activity_type = ?, expected_attendance = ?,
                   reserve_date = ?, start_time = ?, end_time = ?, description = ?, status = ?,
                   reject_reason = NULL, updated_at = ? WHERE id = ?""", (*fields, current, reservation_id),
            )
            db.execute("DELETE FROM reservation_equipments WHERE reservation_id = ?", (reservation_id,))
        db.executemany(
            "INSERT INTO reservation_equipments(reservation_id, equipment_id, quantity) VALUES (?, ?, ?)",
            ((reservation_id, equipment_id, quantity) for equipment_id, quantity in equipment),
        )
        row = find_reservation(db, reservation_id)
        append_audit(db, "SAVE_DRAFT" if draft else "SUBMIT", user["id"], current, row)
        return reservation_view(db, row, user, detailed=True)


def delete_draft(db: sqlite3.Connection, user: sqlite3.Row, reservation_id: int) -> None:
    with transaction(db):
        row = find_reservation(db, reservation_id)
        if row["user_id"] != user["id"]:
            raise ApiError("无权删除此申请。", 403)
        if row["status"] != Status.DRAFT:
            raise ApiError("只有草稿可删除。", 409)
        append_audit(db, "DELETE_DRAFT", user["id"], timestamp(), row, row["title"])
        db.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))


def review(db: sqlite3.Connection, user: sqlite3.Row, reservation_id: int, data: dict[str, Any]) -> dict[str, Any]:
    decision = data.get("decision")
    if decision not in ("APPROVED", "REJECTED"):
        raise ApiError("请选择审批结果。")
    comment = text(data, "comment", "审批意见", required=False, limit=1000)
    if decision == "REJECTED" and len(comment) < 5:
        raise ApiError("请填写不少于 5 个字的驳回原因。", field="comment")
    with transaction(db):
        row = find_reservation(db, reservation_id)
        if user["role"] == Role.ADVISOR and row["department"] != user["department"]:
            raise ApiError("无权审批其他单位的申请。", 403)
        if not can_review(user, row):
            raise ApiError("该申请已处理或尚未流转到当前审批环节。", 409)
        teacher = user["role"] == Role.ADVISOR
        if decision == "APPROVED":
            venue = find_venue(db, row["venue_code"])
            interval = row["reserve_date"], row["start_time"], row["end_time"]
            validate_slot(db, venue, *interval, row["expected_attendance"], reservation_id)
            validate_items(db, equipment_for(db, reservation_id), interval)
            status = Status.PENDING_VENUE if teacher else Status.APPROVED
            action = "APPROVE_ADVISOR" if teacher else "APPROVE_VENUE"
        else:
            status = Status.REJECTED
            action = "REJECT_ADVISOR" if teacher else "REJECT_VENUE"
        current = timestamp()
        db.execute("UPDATE reservations SET status = ?, updated_at = ?, reject_reason = ? WHERE id = ?",
                   (status, current, comment if status == Status.REJECTED else None, reservation_id))
        append_audit(db, action, user["id"], current, row, comment)
        return {"status": status, "message": AUDIT_LABELS[action] + "。"}


def cancel(db: sqlite3.Connection, user: sqlite3.Row, reservation_id: int) -> None:
    with transaction(db):
        row = find_reservation(db, reservation_id)
        if row["user_id"] != user["id"] and user["role"] not in (Role.MANAGER, Role.ADMIN):
            raise ApiError("无权取消此申请。", 403)
        if not can_cancel(user, row):
            message = ("仅可在活动开始前至少 2 小时取消待审核或已批准的预约。"
                       if row["user_id"] == user["id"] else "仅可在活动开始前取消待审核或已批准的预约。")
            raise ApiError(message, 409)
        current = timestamp()
        db.execute("UPDATE reservations SET status = ?, updated_at = ? WHERE id = ?", (Status.CANCELLED, current, reservation_id))
        append_audit(db, "CANCEL", user["id"], current, row)


def reschedule(db: sqlite3.Connection, user: sqlite3.Row, reservation_id: int, data: dict[str, Any]) -> None:
    day, start, end = period(data, booking=True)
    comment = text(data, "comment", "调整原因", required=False, limit=500)
    code = text(data, "venue", "场地编号", limit=32)
    with transaction(db):
        row = find_reservation(db, reservation_id)
        if row["status"] != Status.APPROVED or start_datetime(row) <= now():
            raise ApiError("仅可调整已批准且尚未开始的预约。", 409)
        venue = find_venue(db, code)
        validate_slot(db, venue, day, start, end, row["expected_attendance"], reservation_id)
        validate_items(db, equipment_for(db, reservation_id), (day, start, end), exclude=reservation_id)
        current = timestamp()
        db.execute(
            "UPDATE reservations SET venue_id = ?, reserve_date = ?, start_time = ?, end_time = ?, updated_at = ? WHERE id = ?",
            (venue["id"], day, start, end, current, reservation_id),
        )
        previous = f"{row['venue_code']} {row['reserve_date']} {row['start_time']}–{row['end_time']}"
        updated = f"{venue['venue_code']} {day} {start}–{end}"
        info = f"{previous} 调整为 {updated}。" + (f" {comment}" if comment else "")
        append_audit(db, "RESCHEDULE", user["id"], current, row, info)


def finish_expired(db: sqlite3.Connection) -> None:
    current = timestamp()
    expired = "status = ? AND reserve_date || ' ' || end_time || ':00' <= ?"
    args = (Status.APPROVED, current)
    if not db.execute(f"SELECT 1 FROM reservations WHERE {expired} LIMIT 1", args).fetchone():
        return
    with transaction(db):
        operator = db.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
        rows = db.execute(f"SELECT id, reservation_code FROM reservations WHERE {expired}", args).fetchall()
        db.execute(f"UPDATE reservations SET status = ?, updated_at = ? WHERE {expired}", (Status.FINISHED, current, *args))
        for row in rows:
            append_audit(db, "FINISH", operator["id"], current, row, "活动到期，系统自动归档。")
