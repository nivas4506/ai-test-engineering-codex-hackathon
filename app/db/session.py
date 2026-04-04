from __future__ import annotations

import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_ECHO, DATABASE_POOL_PRE_PING, DATABASE_POOL_RECYCLE, DATABASE_URL
from app.db.base import Base


_engine_kwargs: dict = {
    "echo": DATABASE_ECHO,
    "pool_pre_ping": DATABASE_POOL_PRE_PING,
}
if DATABASE_POOL_RECYCLE > 0:
    _engine_kwargs["pool_recycle"] = DATABASE_POOL_RECYCLE

if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)
logger = logging.getLogger(__name__)


def init_database() -> None:
    from app.db import models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        _run_lightweight_migrations()
    except Exception as exc:
        logger.warning("Database initialization failed. Verify DATABASE_URL and MySQL availability. Error: %s", exc)


def get_db_session() -> Session:
    return SessionLocal()


def _run_lightweight_migrations() -> None:
    inspector = inspect(engine)
    if "run_records" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("run_records")}
    if "owner_user_id" in columns:
        return

    ddl = "ALTER TABLE run_records ADD COLUMN owner_user_id INTEGER"
    if not DATABASE_URL.startswith("sqlite"):
        ddl = "ALTER TABLE run_records ADD COLUMN owner_user_id INTEGER NULL"

    with engine.begin() as connection:
        connection.execute(text(ddl))
