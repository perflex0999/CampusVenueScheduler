import pytest

from app.schemas import ApiError, date_value, integer, period, text, time_value


def test_text_strips_and_returns_value():
    assert text({"title": "  活动  "}, "title", "活动名称") == "活动"


def test_text_required_missing_raises():
    with pytest.raises(ApiError):
        text({}, "title", "活动名称")


def test_text_exceeds_limit_raises():
    with pytest.raises(ApiError):
        text({"title": "x" * 129}, "title", "活动名称", limit=128)


def test_integer_accepts_numeric_string():
    assert integer("12", "数量") == 12


def test_integer_rejects_garbage():
    with pytest.raises(ApiError):
        integer("abc", "数量")


def test_time_value_enforces_30_minute_steps():
    assert time_value("14:30", "start") == "14:30"
    assert time_value("00:00", "start") == "00:00"
    with pytest.raises(ApiError):
        time_value("14:15", "start")


def test_date_value_accepts_iso():
    assert date_value("2099-01-01") == "2099-01-01"


def test_date_value_rejects_invalid():
    with pytest.raises(ApiError):
        date_value("2023-13-40")


def test_period_valid_returns_triple():
    assert period({"date": "2099-01-01", "start": "14:00", "end": "16:00"}) == (
        "2099-01-01", "14:00", "16:00",
    )


def test_period_booking_rejects_too_short():
    with pytest.raises(ApiError):
        period({"date": "2099-01-01", "start": "14:00", "end": "14:00"}, booking=True)


def test_period_booking_rejects_too_long():
    with pytest.raises(ApiError):
        period({"date": "2099-01-01", "start": "08:00", "end": "17:00"}, booking=True)


def test_period_non_booking_requires_end_after_start():
    with pytest.raises(ApiError):
        period({"date": "2099-01-01", "start": "16:00", "end": "15:00"})
