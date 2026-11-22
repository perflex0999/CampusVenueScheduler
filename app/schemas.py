import re
from datetime import date, datetime

from app.config import ACTIVITY_TYPES, CAMPUS_TIMEZONE


class ApiError(Exception):
    def __init__(self, message, status=400, *, field=None):
        super().__init__(message)
        self.status = status
        self.field = field


def now():
    return datetime.now(CAMPUS_TIMEZONE).replace(tzinfo=None, microsecond=0)


def timestamp():
    return now().isoformat(sep=" ")


def text(data, key, label, *, required=True, limit=128):
    value = data.get(key, "")
    if not isinstance(value, str):
        raise ApiError(f"{label}格式不正确。", field=key)
    value = value.strip()
    if required and not value:
        raise ApiError(f"请填写{label}。", field=key)
    if len(value) > limit:
        raise ApiError(f"{label}最多填写 {limit} 个字符。", field=key)
    return value


def integer(value, label, *, minimum=0, maximum=None, field=None):
    if type(value) is int or isinstance(value, str) and re.fullmatch(r"-?[0-9]{1,12}", value):
        number = int(value)
        if minimum <= number <= (maximum if maximum is not None else 2_147_483_647):
            return number
    raise ApiError(f"请填写有效的{label}。", field=field)


def flag(data, key):
    value = data.get(key)
    if type(value) is not bool:
        raise ApiError("请选择有效状态。", field=key)
    return value


def reference_code(data, label):
    value = text(data, "id", label, limit=32).upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]*", value):
        raise ApiError(f"{label}只能使用字母、数字、连字符和下划线。", field="id")
    return value


def date_value(value):
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() == value:
            return value
    except (ValueError, TypeError):
        pass
    raise ApiError("请选择有效的日期。", field="date")


def time_value(value, field):
    if isinstance(value, str) and re.fullmatch(r"(?:[01][0-9]|2[0-3]):(?:00|30)", value):
        return value
    raise ApiError("请选择有效时间，时间以 30 分钟为单位。", field=field)


def period(data, *, booking=False):
    day = date_value(data.get("date"))
    start = time_value(data.get("start"), "start")
    end = time_value(data.get("end"), "end")
    start_at = datetime.fromisoformat(f"{day}T{start}")
    end_at = datetime.fromisoformat(f"{day}T{end}")
    hours = (end_at - start_at).total_seconds() / 3600
    if booking and not 0.5 <= hours <= 8:
        raise ApiError("活动时长须为 30 分钟至 8 小时。", field="end")
    if not booking and hours <= 0:
        raise ApiError("结束时间须晚于开始时间。", field="end")
    return day, start, end


def booking_input(data, *, draft=False):
    activity = text(data, "type", "活动类型")
    if activity not in ACTIVITY_TYPES:
        raise ApiError("请选择活动类型。", field="type")
    quantities = data.get("equipment", {})
    if not isinstance(quantities, dict):
        raise ApiError("借用物资格式不正确。", field="equipment")
    quantities = {
        code: integer(value, "借用数量", field="equipment")
        for code, value in quantities.items()
    }
    day, start, end = period(data, booking=not draft)
    return {
        "title": text(data, "title", "活动名称"),
        "type": activity,
        "people": (None if draft and data.get("people") in (None, "", 0)
                   else integer(data.get("people"), "预期参加人数", minimum=1, field="people")),
        "description": text(data, "description", "活动方案", required=not draft, limit=4000),
        "venue": text(data, "venue", "预约场地", limit=32),
        "date": day, "start": start, "end": end,
        "equipment": {code: qty for code, qty in quantities.items() if qty},
    }


def password_value(data, key="password", *, required=True):
    value = data.get(key, "")
    if value == "" and not required:
        return ""
    if not isinstance(value, str) or not 6 <= len(value) <= 128:
        raise ApiError("新密码长度须为 6 至 128 个字符。", field=key)
    return value
