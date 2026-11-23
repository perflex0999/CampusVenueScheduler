from datetime import timedelta

from flask import Blueprint, g, jsonify, request, session

from app.config import ACTIVITY_TYPES
from app.database import get_db, transaction
from app.models import Role, Status
from app.schemas import ApiError, date_value, now, period
from app.seed import populate_demo
from app.services import auth_service as auth
from app.services import booking_service as booking
from app.services import equipment_service as equipment
from app.services import venue_service as venues

api = Blueprint("api", __name__, url_prefix="/api")


@api.before_request
def require_json():
    if request.method in ("POST", "PATCH", "DELETE"):
        if not request.is_json:
            raise ApiError("请求须使用 JSON 格式。", 415)
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            raise ApiError("请求数据格式不正确。")
        g.payload = payload


@api.after_request
def disable_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@api.post("/auth/login")
def login():
    return auth.login(get_db(), g.payload)


@api.post("/auth/logout")
@auth.require_user()
def logout():
    session.clear()
    return {"message": "已退出登录。"}


@api.patch("/auth/profile")
@auth.require_user()
def profile():
    auth.update_profile(get_db(), g.user, g.payload)
    return {"message": "联系信息已保存。"}


@api.patch("/auth/password")
@auth.require_user()
def password():
    auth.change_password(get_db(), g.user, g.payload)
    return {"message": "密码已修改。"}


@api.get("/workspace")
@auth.require_user()
def workspace():
    db, user = get_db(), g.user
    booking.finish_expired(db)
    role = user["role"]
    current = now().date()
    with transaction(db, write=False):
        result = {
            "account": auth.public_user(user), "profile": {"phone": user["phone"], "email": user["email"]},
            "today": current.isoformat(), "suggestedDate": (current + timedelta(days=3)).isoformat(),
            "activityTypes": ACTIVITY_TYPES, "venues": venues.list_venues(db, {}, paginate=False),
            "equipment": equipment.inventory(db, include_inactive=True),
            "reservations": [], "locks": [], "users": [], "audit": [],
        }
        if role == Role.ADMIN:
            result["users"] = [auth.public_user(row) for row in db.execute("SELECT * FROM users ORDER BY id")]
            result["audit"] = booking.audit_entries(db)
        else:
            records = {row["id"]: row for row in booking.list_schedule(db, user)}
            private = booking.list_own(db, user) if role == Role.STUDENT else booking.list_pending(db, user)
            records.update((row["id"], row) for row in private)
            result["reservations"] = list(records.values())
            result["locks"] = venues.lock_views(db)
    return result


@api.get("/venues")
@auth.require_user()
def venue_list():
    with transaction(get_db(), write=False):
        return venues.list_venues(get_db(), request.args)


@api.get("/venues/<venue_id>")
@auth.require_user()
def venue_detail(venue_id):
    return venues.venue_view(venues.find_venue(get_db(), venue_id))


@api.get("/venues/<venue_id>/schedule")
@auth.require_user()
def venue_schedule(venue_id):
    db = get_db()
    day = date_value(request.args.get("date"))
    booking.finish_expired(db)
    with transaction(db, write=False):
        row = venues.find_venue(db, venue_id)
        return {"venue": venues.venue_view(row), "date": day, "locks": venues.lock_views(db, row["id"], day),
                "reservations": booking.list_schedule(db, g.user, row["id"], day)}


@api.post("/venues")
@auth.require_user(Role.MANAGER)
def add_venue():
    venues.save_venue(get_db(), g.user, g.payload)
    return {"message": "场地已添加。"}, 201


@api.patch("/venues/<venue_id>")
@auth.require_user(Role.MANAGER)
def edit_venue(venue_id):
    venues.save_venue(get_db(), g.user, g.payload, venue_id)
    return {"message": "场地信息已保存。"}


@api.post("/venue-locks")
@auth.require_user(Role.MANAGER)
def add_lock():
    venues.save_lock(get_db(), g.user, g.payload)
    return {"message": "已保存场地锁定。"}, 201


@api.delete("/venue-locks/<int:lock_id>")
@auth.require_user(Role.MANAGER)
def remove_lock(lock_id):
    venues.remove_lock(get_db(), g.user, lock_id)
    return {"message": "已解除场地锁定。"}


@api.get("/equipments")
@auth.require_user()
def equipment_list():
    interval = period(request.args) if any(key in request.args for key in ("date", "start", "end")) else None
    db = get_db()
    booking.finish_expired(db)
    with transaction(db, write=False):
        return {"items": equipment.inventory(db, include_inactive=g.user["role"] == Role.MANAGER, interval=interval)}


@api.post("/equipments")
@auth.require_user(Role.MANAGER)
def add_equipment():
    equipment.save_equipment(get_db(), g.user, g.payload)
    return {"message": "物资已添加。"}, 201


@api.patch("/equipments/<equipment_id>")
@auth.require_user(Role.MANAGER)
def edit_equipment(equipment_id):
    equipment.save_equipment(get_db(), g.user, g.payload, equipment_id)
    return {"message": "物资信息已保存。"}


@api.get("/reservations/my")
@auth.require_user(Role.STUDENT)
def my_reservations():
    db = get_db()
    booking.finish_expired(db)
    with transaction(db, write=False):
        return {"items": booking.list_own(db, g.user)}


@api.post("/reservations")
@auth.require_user(Role.STUDENT)
def add_reservation():
    return booking.save_reservation(get_db(), g.user, g.payload), 201


@api.get("/reservations/<int:reservation_id>")
@auth.require_user()
def reservation_detail(reservation_id):
    db = get_db()
    booking.finish_expired(db)
    with transaction(db, write=False):
        row = booking.find_reservation(db, reservation_id)
        detailed = row["user_id"] == g.user["id"] or booking.can_review(g.user, row)
        if not detailed and row["status"] not in (Status.APPROVED, Status.PENDING_VENUE, Status.FINISHED):
            raise ApiError("无权查看此申请。", 403)
        return booking.reservation_view(db, row, g.user, detailed=detailed)


@api.patch("/reservations/<int:reservation_id>")
@auth.require_user(Role.STUDENT)
def edit_reservation(reservation_id):
    return booking.save_reservation(get_db(), g.user, g.payload, reservation_id)


@api.delete("/reservations/<int:reservation_id>")
@auth.require_user(Role.STUDENT)
def delete_reservation(reservation_id):
    booking.delete_draft(get_db(), g.user, reservation_id)
    return {"message": "草稿已删除。"}


@api.post("/reservations/<int:reservation_id>/cancel")
@auth.require_user(Role.STUDENT, Role.MANAGER, Role.ADMIN)
def cancel_reservation(reservation_id):
    booking.cancel(get_db(), g.user, reservation_id)
    return {"message": "预约已取消。"}


@api.patch("/reservations/<int:reservation_id>/schedule")
@auth.require_user(Role.MANAGER)
def reschedule_reservation(reservation_id):
    booking.reschedule(get_db(), g.user, reservation_id, g.payload)
    return {"message": "预约排期已调整。"}


@api.get("/approvals/pending")
@auth.require_user(Role.ADVISOR, Role.MANAGER)
def pending_approvals():
    db = get_db()
    with transaction(db, write=False):
        return {"items": booking.list_pending(db, g.user, request.args.get("sort"))}


@api.post("/approvals/<int:reservation_id>/audit")
@auth.require_user(Role.ADVISOR, Role.MANAGER)
def review_reservation(reservation_id):
    return booking.review(get_db(), g.user, reservation_id, g.payload)


@api.patch("/admin/users/<username>")
@auth.require_user(Role.ADMIN)
def update_user(username):
    auth.update_user(get_db(), g.user, username, g.payload)
    return {"message": "账号设置已保存。"}


@api.get("/admin/audit")
@auth.require_user(Role.ADMIN)
def audit_list():
    db = get_db()
    booking.finish_expired(db)
    return jsonify(items=booking.audit_entries(db))


@api.post("/admin/reset-demo")
@auth.require_user(Role.ADMIN)
def reset_demo():
    populate_demo(get_db(), operator_name=g.user["username"])
    session.clear()
    return {"message": "演示数据已恢复，请重新登录。"}
