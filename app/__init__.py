"""
Application factory for the Inventory & Task Manager.

Wires together the Flask app, the raw-SQL database layer, and the
route blueprints. Kept deliberately explicit (no ORM) so the SQL
layer stays visible rather than hidden behind auto-generated queries.
"""

import os
from flask import Flask

from app.db import init_db, close_conn


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)

    app.config.from_mapping(
        DATABASE=os.path.join(app.instance_path, "inventory.db"),
        TESTING=False,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    with app.app_context():
        init_db(app.config["DATABASE"])

    app.teardown_appcontext(close_conn)

    from app.routes.items import items_bp
    from app.routes.tasks import tasks_bp
    from app.routes.orders import orders_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(items_bp, url_prefix="/api/items")
    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
    app.register_blueprint(orders_bp, url_prefix="/api/orders")
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    @app.get("/")
    def health():
        return {"status": "ok", "service": "inventory-task-manager"}

    return app
