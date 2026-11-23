# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CampusVenueScheduler — a self-contained campus activity / venue booking system (活动申报 → 场地预约 → 物资借调 → 两级审批 → 排期日历). Students submit reservation requests; advisors (指导教师) give first-level approval, venue managers (场地管理员) give final approval; admins manage accounts, audit logs, and demo-data reset.

The authoritative spec lives in `docs/` (SRS, database/algorithm design, deployment manual) and `docs/adr/` (architecture decision records). The implementation is authoritative over the docs where they diverge (see "Gotchas" below).

## Commands

```bash
python -m pip install -r requirements.txt        # Flask + Werkzeug (runtime)
python -m pip install -r requirements-dev.txt    # pytest + pytest-cov + ruff (dev)
python -m scripts.run_server                     # run app at http://127.0.0.1:8000
python -m scripts.init_db                        # force-reset the SQLite DB to demo data
python -m pytest                                 # run the test suite (tests/)
python -m pytest --cov=app --cov-report=term-missing   # run with coverage (target ≥80%)
python -m ruff check .                           # lint (config in pyproject.toml)
docker build -t campus-venue-scheduler .         # build container image
docker run -p 8000:8000 -v campus-venue-data:/app/var campus-venue-scheduler   # run container
```

Tests live in `tests/` (pytest, ~90% line coverage via `pytest-cov`); `ruff` is the linter (configured in `pyproject.toml`). There is no type-checker and no front-end build step — static assets are served as-is.

CI runs in `.github/workflows/ci.yml` (ruff lint + a Python/OS test matrix with an 80% coverage gate). Pushing a `v*` tag runs `.github/workflows/release.yml` (auto Release Notes + GHCR Docker image).

First launch of `run_server` auto-creates `var/campus_scheduler.sqlite3` and seeds it if empty (`populate_demo(db, reset=False)`). `scripts/init_db` always wipes and re-seeds. Both seed 5 users, 12 venues, 8 equipment types, 18 reservations, and 3 venue locks, with reservation dates anchored 3 days after initialization.

Demo accounts (see `app/seed.py`): `student_01`, `student_02`, `advisor_01`, `manager_01` all use password `123456`; `admin` uses `admin123`.

## Architecture

Stack: **Python 3.12+ + Flask 3.1** (not FastAPI — see Gotchas), **SQLite** (raw SQL, no ORM), and a **single-page front end** in vanilla JS (no framework, no build). Backend is a thin layered monolith:

- `app/main.py` — application factory `create_app(database=...)`; there is **no** module-level `app`, so importing `app.main` has no side effects. `scripts/run_server.py` calls the factory. Registers the `/` route, the `ApiError` handler, and a catch-all JSON 500 handler.
- `app/api.py` — the only HTTP layer. A Flask `Blueprint` at `/api`. Routes are thin: decode/validate via `schemas`, then delegate to a `services/*` function. `@api.before_request` requires JSON bodies for POST/PATCH/DELETE; `@api.after_request` sets `Cache-Control: no-store`.
- `app/services/` — all business logic: `auth_service.py` (login, session, password, account admin), `booking_service.py` (reservation lifecycle, conflict/validation, approvals, cancel/reschedule), `venue_service.py` (venues, locks, overlap queries), `equipment_service.py` (inventory + availability).
- `app/models.py` — the **entire schema is a raw SQL string** (`SCHEMA`) executed via `executescript`; there are no model classes. Also holds `Role`/`Status` `StrEnum`s, `OCCUPYING`/`PENDING` status tuples, `AUDIT_LABELS`, and the `append_audit` helper.
- `app/schemas.py` — request validation/parsing helpers (`text`, `integer`, `flag`, `period`, `booking_input`, …). Raise `ApiError(message, status, field=...)` for validation failures; `main.py` registers an error handler that renders it as `{message, field}`.
- `app/database.py` — SQLite access. `connect()` sets `row_factory = sqlite3.Row`, `PRAGMA foreign_keys = ON`, WAL mode. `transaction(db, write=True)` is a context manager (uses `BEGIN IMMEDIATE` for writes). Per-request DB is stashed on `flask.g` via `get_db()`.
- `app/config.py` — paths, `CAMPUS_TIMEZONE` (Asia/Shanghai), `ACTIVITY_TYPES`, page size.
- `app/seed.py` — demo data (`populate_demo`).
- `app/templates/index.html` + `app/static/scheduler.js` + `app/static/styles.css` — front end. `index.html` is an empty shell; `scheduler.js` (~800 lines) is a hash-routed SPA that renders the whole UI from template strings and talks to the `/api` JSON endpoints.

### Key conventions

- **Role & status enums are strings**, not ints: `Role = student|advisor|manager|admin`; reservation `Status` state machine is `DRAFT → PENDING_ADVISOR → PENDING_VENUE → APPROVED`, with terminal `REJECTED / CANCELLED / FINISHED`. Approval routing depends on role: advisor approves `PENDING_ADVISOR`, manager approves `PENDING_VENUE`; an advisor may only review reservations from their own `department`.
- **Auth is Flask session-based.** `session` stores `uid` + `version`; `current_user()` re-reads the `users` row each request and matches `users.auth_version`. Any password/role/enable change bumps `auth_version`, which force-invalidates other sessions. `auth.require_user(*roles)` is the authorization decorator. Login lockout after 5 failures (`login_attempts` table).
- **Time is stored as `"HH:MM"` strings** in 30-minute granularity; `reserve_date` is `"YYYY-MM-DD"`. All validation enforces 30-min steps (`schemas.time_value`) and a 0.5–8h duration for bookings. Server "now" is `schemas.now()` (Asia/Shanghai, microseconds stripped).
- **Conflict detection uses half-open intervals `[start, end)`** — overlap iff `existing.start < new.end AND new.start < existing.end`, so back-to-back slots are legal. `OCCUPYING = (APPROVED, PENDING_VENUE)` are the statuses that block a slot. Implemented in `venue_service.overlapping_reservation` / `overlapping_lock`.
- **Equipment availability** counts only `APPROVED` reservations overlapping the interval (not `PENDING_VENUE`): `available = total_qty - sum(occupied)`, in `equipment_service.available_quantities`.
- **`finish_expired(db)`** lazily flips past-`end_time` `APPROVED` reservations to `FINISHED` and writes an audit entry; it is invoked at the top of most read endpoints, so reads can have write side effects.
- **Audit trail**: every mutation calls `append_audit` into `audit_logs` (`AUDIT_LABELS` maps action codes to Chinese labels shown in the UI). The `settings` table persists the Flask `secret_key` so sessions survive restarts.

## Gotchas

- The `docs/` (there is no `README.md`) were written against an earlier/planned design and **differ from the code**: docs say "FastAPI or Flask" and reference `tests/`, `check_venue_conflict`, and a `get_available_equipment` function — the actual code is Flask-only, has no tests, and implements the equivalents as `venue_service.overlapping_reservation` and `equipment_service.available_quantities`. Trust the code, and update docs only if asked.
- Only `Flask` and `Werkzeug` are pinned in `requirements.txt`. Do not assume `pytest`, `uvicorn`, etc. are available.
- Data is at `var/campus_scheduler.sqlite3` (`var/` is gitignored). Reset via `scripts/init_db` or the admin "数据初始化" page clears reservations/settings/audit **and invalidates all sessions** (the session key is regenerated).
- The front end's `api()` wrapper throws on any non-2xx, attaching `status` and `field`; a `401` triggers a client-side logout. UI text and API messages are **Chinese** — keep new copy consistent.
- `find_venue` accepts either a `venue_code` or a numeric id string (case-insensitive code match), so routes/fields that say `venue` may carry either form.
