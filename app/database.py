from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from flask import g

from app.models import SCHEMA


def connect(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize_schema(db: sqlite3.Connection) -> None:
    db.execute("PRAGMA journal_mode = WAL")
    db.executescript(SCHEMA)


@contextmanager
def transaction(db: sqlite3.Connection, *, write: bool = True) -> Iterator[None]:
    db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        from flask import current_app

        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()
