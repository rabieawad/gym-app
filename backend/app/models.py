"""Database tables.

To add a feature, add a model here (or a new module that imports Base), make sure it is
imported before startup, and add a router in app/routers/. Tables are created on startup
with create_all(); when you start changing existing tables, add Alembic migrations.
"""
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(60))
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    exercises: Mapped[list["Exercise"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
    lifts: Mapped[list["LiftEntry"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Exercise(Base):
    """A movement. user_id is NULL for built-in exercises, set for a member's own."""

    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )

    owner: Mapped[User | None] = relationship(back_populates="exercises")


class LiftEntry(Base):
    """One logged lift: `sets` sets of `reps` reps at `weight_kg`."""

    __tablename__ = "lift_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), index=True)
    weight_kg: Mapped[float] = mapped_column(Float)
    reps: Mapped[int] = mapped_column(Integer)
    sets: Mapped[int] = mapped_column(Integer, default=1)
    performed_on: Mapped[date] = mapped_column(Date, index=True)
    notes: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="lifts")
    exercise: Mapped[Exercise] = relationship()
