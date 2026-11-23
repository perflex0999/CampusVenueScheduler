from __future__ import annotations

import sqlite3
from typing import Any

from app.database import transaction
from app.models import Status, append_audit
from app.schemas import ApiError, flag, integer, reference_code, text, timestamp


def available_quantities(db: sqlite3.Connection, day: str, start: str, end: str,
                         exclude: int | None = None) -> dict[int, int]:
    rows = db.execute(
        """SELECT e.id, sum(re.quantity) AS occupied FROM reservations r
           JOIN reservation_equipments re ON re.reservation_id = r.id
           JOIN equipments e ON e.id = re.equipment_id
           WHERE r.status = ? AND r.reserve_date = ? AND r.start_time < ? AND ? < r.end_time
           AND (? IS NULL OR r.id <> ?)
           GROUP BY e.id""",
        (Status.APPROVED, day, end, start, exclude, exclude),
    )
    return {row["id"]: row["occupied"] for row in rows}


def inventory(db: sqlite3.Connection, *, include_inactive: bool = False,
              interval: tuple[str, str, str] | None = None) -> list[dict[str, Any]]:
    occupied = available_quantities(db, *interval) if interval else {}
    rows = db.execute("SELECT * FROM equipments WHERE is_active = 1 OR ? ORDER BY id", (include_inactive,))
    result = []
    for row in rows:
        item = {
            "id": row["equipment_code"], "name": row["name"], "total": row["total_qty"],
            "limit": row["max_per_booking"], "unit": row["unit"], "enabled": bool(row["is_active"]),
        }
        if interval:
            item["available"] = max(0, row["total_qty"] - occupied.get(row["id"], 0))
        result.append(item)
    return result


def validate_items(db: sqlite3.Connection, requested: dict[str, int], interval: tuple[str, str, str], *,
                   draft: bool = False, exclude: int | None = None) -> list[tuple[int, int]]:
    if not requested:
        return []
    occupied = {} if draft else available_quantities(db, *interval, exclude=exclude)
    rows = {row["equipment_code"]: row for row in db.execute("SELECT * FROM equipments")}
    validated = []
    for code, quantity in requested.items():
        item = rows.get(code)
        if not item or not item["is_active"]:
            raise ApiError(f"物资 {item['name'] if item else code} 当前不可借用。", field="equipment")
        remaining = max(0, item["total_qty"] - occupied.get(item["id"], 0))
        if not draft and (quantity > item["max_per_booking"] or quantity > remaining):
            raise ApiError(
                f"请调整{item['name']}借用数量，单次限借 {item['max_per_booking']}，该时段可借 {remaining}。",
                409, field="equipment",
            )
        validated.append((item["id"], quantity))
    return validated


def save_equipment(db: sqlite3.Connection, operator: sqlite3.Row, data: dict[str, Any], code: str | None = None) -> None:
    values = (
        text(data, "name", "物资名称", limit=64), integer(data.get("total"), "总库存", field="total"),
        integer(data.get("limit"), "单次限借", minimum=1, field="limit"),
        text(data, "unit", "计量单位", limit=16), flag(data, "enabled"),
    )
    with transaction(db):
        if code is None:
            code = reference_code(data, "物资编号")
            if db.execute("SELECT 1 FROM equipments WHERE equipment_code = ?", (code,)).fetchone():
                raise ApiError("该物资编号已存在。", 409, field="id")
            db.execute(
                "INSERT INTO equipments(equipment_code, name, total_qty, max_per_booking, unit, is_active) VALUES (?, ?, ?, ?, ?, ?)",
                (code, *values),
            )
        else:
            updated = db.execute(
                """UPDATE equipments SET name = ?, total_qty = ?, max_per_booking = ?, unit = ?, is_active = ?
                   WHERE equipment_code = ?""",
                (*values, code),
            )
            if not updated.rowcount:
                raise ApiError("物资不存在。", 404)
        append_audit(db, "SAVE_EQUIPMENT", operator["id"], timestamp(), comment=code)
