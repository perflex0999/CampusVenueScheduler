from datetime import timedelta
from secrets import token_urlsafe

from app.config import ACTIVITY_TYPES
from app.database import transaction
from app.models import Status, append_audit
from app.schemas import now, timestamp
from app.services.auth_service import password_hash

USERS = (
    ("student_01", "李晓峰", "student", "计算机学院"),
    ("student_02", "张嘉仪", "student", "计算机学院"),
    ("advisor_01", "赵明远", "advisor", "计算机学院"),
    ("manager_01", "孙建国", "manager", "教务处"),
    ("admin", "系统管理员", "admin", "信息化办公室"),
)

VENUES = (
    ("ZJ-101", "综教楼 101 多媒体报告厅", "综教楼", 150, "报告厅", "投影幕布、讲台电脑、扩声系统", "08:00", "22:00", "AVAILABLE"),
    ("ZJ-205", "综教楼 205 多媒体教室", "综教楼", 60, "多媒体教室", "投影仪、讲台电脑、白板", "08:00", "22:00", "AVAILABLE"),
    ("XH-203", "学活中心 203 学生活动室", "学活中心", 45, "活动室", "移动桌椅、音响、白板", "08:00", "22:00", "AVAILABLE"),
    ("XK-312", "信科楼 312 会议室", "信科楼", 24, "会议室", "会议桌、显示屏、白板", "08:00", "21:00", "AVAILABLE"),
    ("TY-01", "体育馆 多功能厅", "体育馆", 200, "体育馆", "扩声系统、活动座椅", "08:00", "22:00", "MAINTENANCE"),
    ("XH-305", "学活中心 305 排练室", "学活中心", 30, "活动室", "把杆、镜面、音响", "09:00", "21:00", "AVAILABLE"),
    ("ZJ-307", "综教楼 307 阶梯教室", "综教楼", 96, "多媒体教室", "投影仪、无线投屏、扩声系统", "08:00", "21:30", "AVAILABLE"),
    ("XK-118", "信科楼 118 研讨室", "信科楼", 36, "会议室", "移动白板、显示屏、圆桌", "08:30", "21:00", "AVAILABLE"),
    ("XH-110", "学活中心 110 展厅", "学活中心", 80, "活动室", "展墙、轨道灯、接待台", "09:00", "20:30", "AVAILABLE"),
    ("TS-201", "图书馆 201 交流室", "图书馆", 40, "会议室", "显示屏、话筒接口、移动座椅", "09:00", "20:00", "AVAILABLE"),
    ("TS-401", "图书馆 401 学术报告厅", "图书馆", 120, "报告厅", "投影幕布、讲台电脑、录播系统", "08:30", "20:30", "AVAILABLE"),
    ("TY-02", "体育馆 训练室", "体育馆", 55, "体育馆", "储物柜、活动垫、移动音响", "09:00", "21:00", "AVAILABLE"),
)

EQUIPMENT = (
    ("EQ-001", "无线手持麦克风", 12, 5, "支"),
    ("EQ-002", "活动展架", 16, 8, "个"),
    ("EQ-003", "便携音响", 4, 2, "套"),
    ("EQ-004", "翻页笔", 8, 2, "支"),
    ("EQ-005", "移动投影仪", 5, 2, "台"),
    ("EQ-006", "活动折叠桌", 20, 8, "张"),
    ("EQ-007", "电源延长线", 18, 6, "条"),
    ("EQ-008", "立式指示牌", 10, 4, "个"),
)

# The dates are offsets from the demonstration day, three days after initialization.
RESERVATIONS = (
    ("开源技术沙龙", 1, 1, Status.PENDING_ADVISOR, 0, "14:00", "16:30", 80, 0, {1: 2}),
    ("秋季读书交流会", 1, 3, Status.APPROVED, 3, "10:00", "11:30", 32, 0, {}),
    ("计算机科协例会", 1, 2, Status.PENDING_VENUE, 0, "15:00", "16:30", 40, 3, {}),
    ("校园志愿者培训", 2, 1, Status.APPROVED, 0, "09:00", "11:00", 105, 0, {1: 3, 4: 1}),
    ("校园音乐节排练", 2, 3, Status.PENDING_VENUE, 0, "17:00", "19:00", 24, 1, {3: 1}),
    ("社团学期总结会", 1, 4, Status.FINISHED, -8, "13:00", "14:00", 18, 3, {}),
    ("迎新志愿服务交流", 2, 7, Status.APPROVED, 0, "13:00", "14:30", 65, 0, {4: 1}),
    ("校园摄影作品交流", 2, 9, Status.APPROVED, 1, "10:00", "12:00", 48, 2, {2: 5, 8: 2}),
    ("学院辩论队训练", 1, 8, Status.PENDING_ADVISOR, 1, "18:00", "19:30", 20, 1, {}),
    ("校园心理健康讲座", 2, 11, Status.PENDING_ADVISOR, 2, "14:00", "16:00", 90, 0, {1: 2}),
    ("班级学业互助例会", 1, 10, Status.APPROVED, 2, "16:00", "17:30", 24, 3, {}),
    ("文艺社合唱排练", 2, 6, Status.APPROVED, 1, "15:00", "16:30", 21, 1, {3: 2}),
    ("院刊编辑部例会", 1, 4, Status.DRAFT, 4, "18:30", "19:30", 15, 3, {}),
    ("学生活动布展协调会", 2, 9, Status.REJECTED, 4, "10:00", "11:30", 30, 3, {2: 2}),
    ("校园定向活动说明会", 2, 12, Status.CANCELLED, 2, "10:00", "11:00", 35, 0, {3: 1}),
    ("数据结构学习交流", 1, 7, Status.FINISHED, -6, "15:00", "16:30", 53, 0, {4: 1}),
    ("社团纳新材料整理", 2, 3, Status.PENDING_VENUE, 2, "14:30", "16:00", 16, 3, {6: 3}),
    ("学院实践分享会", 1, 11, Status.APPROVED, 6, "19:00", "20:00", 70, 0, {1: 2, 4: 1}),
)


def populate_demo(db, *, operator_name=None, reset=True):
    with transaction(db):
        if not reset and db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            return
        for table in ("audit_logs", "reservation_equipments", "venue_locks", "reservations",
                      "equipments", "venues", "login_attempts", "users"):
            db.execute(f"DELETE FROM {table}")
        db.execute("DELETE FROM sqlite_sequence WHERE name IN ('reservations', 'venue_locks')")
        current = now()
        day = current.date()
        demo_day = day + timedelta(days=3)
        created = (day - timedelta(days=30)).isoformat() + " 08:00:00"
        db.executemany(
            """INSERT INTO users(id, username, real_name, role, department, password_hash, auth_version, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ((index, *user, password_hash("admin123" if user[0] == "admin" else "123456"), token_urlsafe(), created)
             for index, user in enumerate(USERS, 1)),
        )
        db.executemany(
            """INSERT INTO venues(id, venue_code, name, building, capacity, venue_type, equipment_desc,
               open_start, open_end, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ((index, *venue) for index, venue in enumerate(VENUES, 1)),
        )
        db.executemany(
            "INSERT INTO equipments(id, equipment_code, name, total_qty, max_per_booking, unit) VALUES (?, ?, ?, ?, ?, ?)",
            ((index, *item) for index, item in enumerate(EQUIPMENT, 1)),
        )
        for index, example in enumerate(RESERVATIONS, 1):
            seed_reservation(db, index, example, current, demo_day)
        db.executemany(
            "INSERT INTO venue_locks(venue_id, lock_date, start_time, end_time, reason, operator_id) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (2, demo_day.isoformat(), "10:00", "12:00", "教学设备检修", 4),
                (8, demo_day.isoformat(), "14:00", "16:00", "学院面试", 4),
                (9, (demo_day + timedelta(days=2)).isoformat(), "09:00", "11:00", "展厅布置", 4),
            ],
        )
        if operator_name:
            append_audit(db, "RESET_DEMO", 5, timestamp(), comment=f"由 {operator_name} 执行演示数据恢复。")


def seed_reservation(db, index, example, current, demo_day):
    title, user, venue, status, offset, start, end, people, activity_type, equipment = example
    booked = demo_day + timedelta(days=offset)
    created = min(current.date() - timedelta(days=index - 1), booked - timedelta(days=1))
    created_at = created.isoformat() + " 09:00:00"
    if index == 1:
        created_at = current.isoformat(sep=" ")
    code = f"RES-{created.strftime('%Y%m%d')}-{index:03d}"
    description = ("面向学院学生开展开源技术分享，安排主题介绍、项目演示和现场问答。" if index == 1 else
                   f"由校内学生组织开展{title}。由活动负责人组织签到并维持秩序，结束后清理场地并归还物资。")
    reject_reason = "请补充现场人员分工和布展方案。" if status == Status.REJECTED else None
    db.execute(
        """INSERT INTO reservations(id, reservation_code, user_id, venue_id, title, activity_type, expected_attendance,
           reserve_date, start_time, end_time, description, status, reject_reason, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (index, code, user, venue, title, ACTIVITY_TYPES[activity_type], people, booked.isoformat(), start, end,
         description, status, reject_reason, created_at, created_at),
    )
    db.executemany(
        "INSERT INTO reservation_equipments(reservation_id, equipment_id, quantity) VALUES (?, ?, ?)",
        ((index, item, quantity) for item, quantity in equipment.items()),
    )
    record = {"id": index, "reservation_code": code}
    actions = [("SAVE_DRAFT" if status == Status.DRAFT else "SUBMIT", user, created_at, "")]
    if status in (Status.PENDING_VENUE, Status.APPROVED, Status.FINISHED, Status.CANCELLED):
        actions.append(("APPROVE_ADVISOR", 3, created.isoformat() + " 10:00:00", "同意举办，活动方案完整。"))
    if status in (Status.APPROVED, Status.FINISHED, Status.CANCELLED):
        actions.append(("APPROVE_VENUE", 4, created.isoformat() + " 11:00:00", "场地和物资已确认。"))
    if status == Status.CANCELLED:
        actions.append(("CANCEL", user, created.isoformat() + " 13:00:00", "活动时间调整。"))
    if status == Status.REJECTED:
        actions.append(("REJECT_ADVISOR", 3, created.isoformat() + " 11:00:00", reject_reason))
    if status == Status.FINISHED:
        actions.append(("FINISH", 5, f"{booked.isoformat()} {end}:00", "活动到期，系统自动归档。"))
    for action, operator, time, comment in actions:
        append_audit(db, action, operator, time, record, comment)
    db.execute("UPDATE reservations SET updated_at = ? WHERE id = ?", (actions[-1][2], index))
