from __future__ import annotations

import sqlite3
from math import ceil
from typing import Any

from app.config import DEFAULT_PAGE_SIZE
from app.database import transaction
from app.models import OCCUPYING, append_audit
from app.schemas import ApiError, flag, integer, period, reference_code, text, time_value, timestamp


def venue_view(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["venue_code"], "name": row["name"], "building": row["building"],
        "type": row["venue_type"], "capacity": row["capacity"], "setup": row["equipment_desc"],
        "open": row["open_start"], "close": row["open_end"], "maintenance": row["status"] == "MAINTENANCE",
    }


def list_venues(db: sqlite3.Connection, filters: dict[str, Any], *, paginate: bool = True) -> dict[str, Any] | list[dict[str, Any]]:
    clauses: list[str] = []
    parameters: list[Any] = []
    query = text(filters, "q", "搜索词", required=False)
    if query:
        clauses.append("instr(lower(name || ' ' || venue_code), lower(?)) > 0")
        parameters.append(query)
    for key, column in (("building", "building"), ("type", "venue_type"), ("status", "status")):
        if filters.get(key):
            clauses.append(f"{column} = ?")
            parameters.append(filters[key])
    for key, operator in (("min_capacity", ">="), ("max_capacity", "<=")):
        if filters.get(key):
            clauses.append(f"capacity {operator} ?")
            parameters.append(integer(filters[key], "场地容量"))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    select = "SELECT * FROM venues" + where + " ORDER BY id"
    if not paginate:
        return [venue_view(row) for row in db.execute(select, parameters)]
    limit = integer(filters.get("page_size", DEFAULT_PAGE_SIZE), "每页数量", minimum=1, maximum=100)
    page = integer(filters.get("page", 1), "页码", minimum=1)
    count = db.execute("SELECT count(*) FROM venues" + where, parameters).fetchone()[0]
    rows = db.execute(select + " LIMIT ? OFFSET ?", (*parameters, limit, (page - 1) * limit))
    return {"items": [venue_view(row) for row in rows], "total": count, "page": page, "pages": ceil(count / limit)}


def find_venue(db: sqlite3.Connection, code: str) -> sqlite3.Row:
    row = db.execute(
        """SELECT * FROM venues WHERE venue_code = ? COLLATE NOCASE OR CAST(id AS TEXT) = ?
           ORDER BY (venue_code = ? COLLATE NOCASE) DESC LIMIT 1""", (code, code, code),
    ).fetchone()
    if row is None:
        raise ApiError("场地不存在。", 404, field="venue")
    return row


def lock_views(db: sqlite3.Connection, venue_id: int | None = None, day: str | None = None) -> list[dict[str, Any]]:
    rows = db.execute(
        """SELECT l.*, v.venue_code FROM venue_locks l JOIN venues v ON v.id = l.venue_id
           WHERE (? IS NULL OR l.venue_id = ?) AND (? IS NULL OR l.lock_date = ?)
           ORDER BY lock_date, start_time, l.id""",
        (venue_id, venue_id, day, day),
    )
    return [{
        "id": row["id"], "venue": row["venue_code"], "date": row["lock_date"],
        "start": row["start_time"], "end": row["end_time"], "reason": row["reason"],
    } for row in rows]


def overlapping_reservation(db: sqlite3.Connection, venue_id: int, day: str, start: str, end: str,
                            exclude: int | None = None) -> sqlite3.Row | None:
    return db.execute(
        """SELECT title, start_time, end_time FROM reservations
           WHERE venue_id = ? AND reserve_date = ? AND status IN (?, ?) AND start_time < ? AND ? < end_time
           AND (? IS NULL OR id <> ?) ORDER BY start_time, id LIMIT 1""",
        (venue_id, day, *OCCUPYING, end, start, exclude, exclude),
    ).fetchone()


def overlapping_lock(db: sqlite3.Connection, venue_id: int, day: str, start: str, end: str) -> sqlite3.Row | None:
    return db.execute(
        """SELECT reason AS title, start_time, end_time FROM venue_locks
           WHERE venue_id = ? AND lock_date = ? AND start_time < ? AND ? < end_time ORDER BY start_time, id LIMIT 1""",
        (venue_id, day, end, start),
    ).fetchone()


def save_venue(db: sqlite3.Connection, operator: sqlite3.Row, data: dict[str, Any], code: str | None = None) -> None:
    values = (
        text(data, "name", "场地名称", limit=64), text(data, "building", "楼宇", limit=32),
        integer(data.get("capacity"), "场地容量", minimum=1, field="capacity"),
        text(data, "type", "场地类型", limit=32), text(data, "setup", "固定设备", required=False, limit=500),
        time_value(data.get("open"), "open"), time_value(data.get("close"), "close"),
        "MAINTENANCE" if flag(data, "maintenance") else "AVAILABLE",
    )
    if values[5] >= values[6]:
        raise ApiError("闭馆时间须晚于开放时间。", field="close")
    with transaction(db):
        if code is None:
            code = reference_code(data, "场地编号")
            if db.execute("SELECT 1 FROM venues WHERE venue_code = ?", (code,)).fetchone():
                raise ApiError("该场地编号已存在。", 409, field="id")
            db.execute(
                """INSERT INTO venues(venue_code, name, building, capacity, venue_type, equipment_desc,
                   open_start, open_end, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (code, *values),
            )
        else:
            venue = find_venue(db, code)
            db.execute(
                """UPDATE venues SET name = ?, building = ?, capacity = ?, venue_type = ?,
                   equipment_desc = ?, open_start = ?, open_end = ?, status = ? WHERE id = ?""",
                (*values, venue["id"]),
            )
        append_audit(db, "SAVE_VENUE", operator["id"], timestamp(), comment=code)


def save_lock(db: sqlite3.Connection, operator: sqlite3.Row, data: dict[str, Any]) -> None:
    day, start, end = period(data)
    if f"{day} {start}:00" <= timestamp():
        raise ApiError("锁定时段须晚于当前时间。", field="start")
    code = text(data, "venue", "场地编号", limit=32)
    reason = text(data, "reason", "锁定原因", limit=500)
    with transaction(db):
        venue = find_venue(db, code)
        conflict = (overlapping_reservation(db, venue["id"], day, start, end)
                    or overlapping_lock(db, venue["id"], day, start, end))
        if conflict:
            raise ApiError(f"该时段与{conflict['title']}（{conflict['start_time']}–{conflict['end_time']}）重叠。", 409)
        db.execute(
            "INSERT INTO venue_locks(venue_id, lock_date, start_time, end_time, reason, operator_id) VALUES (?, ?, ?, ?, ?, ?)",
            (venue["id"], day, start, end, reason, operator["id"]),
        )
        append_audit(db, "LOCK_VENUE", operator["id"], timestamp(), comment=f"{venue['venue_code']} {day} {start}–{end} {reason}")


def remove_lock(db: sqlite3.Connection, operator: sqlite3.Row, lock_id: int) -> None:
    with transaction(db):
        lock = db.execute(
            "SELECT l.*, v.venue_code FROM venue_locks l JOIN venues v ON l.venue_id = v.id WHERE l.id = ?",
            (lock_id,),
        ).fetchone()
        if lock is None:
            raise ApiError("场地锁定记录不存在。", 404)
        db.execute("DELETE FROM venue_locks WHERE id = ?", (lock_id,))
        append_audit(db, "UNLOCK_VENUE", operator["id"], timestamp(),
                     comment=f"{lock['venue_code']} {lock['lock_date']} {lock['start_time']}–{lock['end_time']}")
