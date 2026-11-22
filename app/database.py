import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import g

from app.models import SCHEMA


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize_schema(db):
    db.execute("PRAGMA journal_mode = WAL")
    db.executescript(SCHEMA)


@contextmanager
def transaction(db, *, write=True):
    db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
    try:
        yield
        db.commit()
    except BaseException:
        db.rollback()
        raise


def get_db():
    if "db" not in g:
        from flask import current_app

        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
