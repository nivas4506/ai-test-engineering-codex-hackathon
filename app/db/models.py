from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RunRecord(Base):
    __tablename__ = "run_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    repository_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), index=True)
    iterations: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=0)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner: Mapped[UserAccount | None] = relationship(back_populates="runs")
    generation_attempts: Mapped[list[RunGenerationAttempt]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    execution_attempts: Mapped[list[RunExecutionAttempt]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )
    debug_attempts: Mapped[list[RunDebugAttempt]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(512))
    password_salt: Mapped[str] = mapped_column(String(255))
    auth_provider: Mapped[str] = mapped_column(String(32), default="password")
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runs: Mapped[list[RunRecord]] = relationship(back_populates="owner")
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"), index=True)
    access_token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[UserAccount] = relationship(back_populates="sessions")


class RunGenerationAttempt(Base):
    __tablename__ = "run_generation_attempts"
    __table_args__ = (UniqueConstraint("run_id", "attempt_index", name="uq_generation_attempt"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run_records.id", ondelete="CASCADE"), index=True)
    attempt_index: Mapped[int] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(16))
    summary: Mapped[str] = mapped_column(Text)
    generated_files_json: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[RunRecord] = relationship(back_populates="generation_attempts")


class RunExecutionAttempt(Base):
    __tablename__ = "run_execution_attempts"
    __table_args__ = (UniqueConstraint("run_id", "attempt_index", name="uq_execution_attempt"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run_records.id", ondelete="CASCADE"), index=True)
    attempt_index: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), index=True)
    exit_code: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[float] = mapped_column(Float)
    tests_collected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str] = mapped_column(Text)
    stderr: Mapped[str] = mapped_column(Text)
    failing_tests_json: Mapped[list] = mapped_column(JSON)
    command_json: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[RunRecord] = relationship(back_populates="execution_attempts")


class RunDebugAttempt(Base):
    __tablename__ = "run_debug_attempts"
    __table_args__ = (UniqueConstraint("run_id", "attempt_index", name="uq_debug_attempt"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("run_records.id", ondelete="CASCADE"), index=True)
    attempt_index: Mapped[int] = mapped_column(Integer)
    diagnosis: Mapped[str] = mapped_column(Text)
    next_generation_mode: Mapped[str] = mapped_column(String(16))
    actions_json: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[RunRecord] = relationship(back_populates="debug_attempts")
