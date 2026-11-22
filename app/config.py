import os
from datetime import timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = Path(os.environ.get("CAMPUS_DATABASE", ROOT / "var" / "campus_scheduler.sqlite3"))
CAMPUS_TIMEZONE = timezone(timedelta(hours=8), "Asia/Shanghai")
ACTIVITY_TYPES = ("学术讲座", "社团排练", "文娱活动", "班级例会")
DEFAULT_PAGE_SIZE = 6
