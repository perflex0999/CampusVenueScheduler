from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    ADVISOR = "advisor"
    MANAGER = "manager"
    ADMIN = "admin"


class Status(StrEnum):
    DRAFT = "DRAFT"
    PENDING_ADVISOR = "PENDING_ADVISOR"
    PENDING_VENUE = "PENDING_VENUE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FINISHED = "FINISHED"


PENDING = (Status.PENDING_ADVISOR, Status.PENDING_VENUE)
OCCUPYING = (Status.APPROVED, Status.PENDING_VENUE)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
    real_name TEXT NOT NULL, role TEXT NOT NULL, department TEXT NOT NULL, phone TEXT DEFAULT '',
    email TEXT DEFAULT '', is_active INTEGER NOT NULL DEFAULT 1,
    auth_version TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS venues (
    id INTEGER PRIMARY KEY, venue_code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    building TEXT NOT NULL, capacity INTEGER NOT NULL CHECK (capacity > 0),
    venue_type TEXT NOT NULL, equipment_desc TEXT NOT NULL DEFAULT '',
    open_start TEXT NOT NULL DEFAULT '08:00', open_end TEXT NOT NULL DEFAULT '22:00',
    status TEXT NOT NULL DEFAULT 'AVAILABLE'
);
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, reservation_code TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id), venue_id INTEGER NOT NULL REFERENCES venues(id),
    title TEXT NOT NULL, activity_type TEXT NOT NULL, expected_attendance INTEGER,
    reserve_date TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, reject_reason TEXT,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS reservation_schedule ON reservations(venue_id, reserve_date, status, start_time, end_time);
CREATE INDEX IF NOT EXISTS reservation_inventory ON reservations(reserve_date, status, start_time, end_time);
CREATE INDEX IF NOT EXISTS reservation_owner ON reservations(user_id, created_at);
CREATE TABLE IF NOT EXISTS equipments (
    id INTEGER PRIMARY KEY, equipment_code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
    total_qty INTEGER NOT NULL CHECK (total_qty >= 0), max_per_booking INTEGER NOT NULL CHECK (max_per_booking > 0),
    unit TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS reservation_equipments (
    id INTEGER PRIMARY KEY, reservation_id INTEGER NOT NULL REFERENCES reservations(id) ON DELETE CASCADE,
    equipment_id INTEGER NOT NULL REFERENCES equipments(id), quantity INTEGER NOT NULL CHECK (quantity > 0),
    UNIQUE (reservation_id, equipment_id)
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY, reservation_id INTEGER REFERENCES reservations(id) ON DELETE SET NULL,
    reservation_code TEXT, operator_id INTEGER NOT NULL REFERENCES users(id),
    action TEXT NOT NULL, comment TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_reservation ON audit_logs(reservation_id, id);
CREATE TABLE IF NOT EXISTS venue_locks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, venue_id INTEGER NOT NULL REFERENCES venues(id),
    lock_date TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
    reason TEXT NOT NULL, operator_id INTEGER NOT NULL REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS venue_lock_schedule ON venue_locks(venue_id, lock_date);
CREATE TABLE IF NOT EXISTS login_attempts (
    username TEXT PRIMARY KEY, failures INTEGER NOT NULL, lock_until TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    name TEXT PRIMARY KEY, value TEXT NOT NULL
);
"""

AUDIT_LABELS = {
    "SAVE_DRAFT": "保存草稿", "DELETE_DRAFT": "删除草稿", "SUBMIT": "提交申请",
    "APPROVE_ADVISOR": "指导教师初审通过", "APPROVE_VENUE": "场地管理员终审批准",
    "REJECT_ADVISOR": "初审驳回", "REJECT_VENUE": "终审驳回", "CANCEL": "取消预约", "RESCHEDULE": "调整排期",
    "FINISH": "活动结束", "SAVE_VENUE": "保存场地", "SAVE_EQUIPMENT": "保存物资",
    "LOCK_VENUE": "锁定场地", "UNLOCK_VENUE": "解除场地锁定", "SAVE_USER": "保存账号",
    "RESET_DEMO": "恢复演示数据",
}


def append_audit(db, action, operator, timestamp, reservation=None, comment=""):
    db.execute(
        """INSERT INTO audit_logs(reservation_id, reservation_code, operator_id, action, comment, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (reservation["id"] if reservation else None, reservation["reservation_code"] if reservation else None,
         operator, action, comment, timestamp),
    )
