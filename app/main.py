from contextlib import closing
from datetime import timedelta
from secrets import token_urlsafe

from flask import Flask, render_template

from app.api import api
from app.config import DATABASE
from app.database import close_db, connect, initialize_schema, transaction
from app.schemas import ApiError
from app.seed import populate_demo


def create_app(database=DATABASE):
    app = Flask(__name__)
    app.config.update(
        DATABASE=database, PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    with closing(connect(database)) as db:
        initialize_schema(db)
        with transaction(db):
            key = db.execute("SELECT value FROM settings WHERE name = 'session_key'").fetchone()
            if key:
                app.secret_key = key["value"]
            else:
                app.secret_key = token_urlsafe(48)
                db.execute("INSERT INTO settings(name, value) VALUES ('session_key', ?)", (app.secret_key,))
        populate_demo(db, reset=False)

    app.teardown_appcontext(close_db)
    app.register_blueprint(api)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(ApiError)
    def api_error(error):
        return {"message": str(error), "field": error.field}, error.status

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        app.logger.error("未处理的服务器错误: %s", error, exc_info=error)
        return {"message": "服务器内部错误，请稍后重试。"}, 500

    return app
