from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Exercise

BUILTIN_EXERCISES = [
    "Back squat",
    "Front squat",
    "Bench press",
    "Incline bench press",
    "Deadlift",
    "Romanian deadlift",
    "Overhead press",
    "Barbell row",
    "Pull-up",
    "Dip",
    "Hip thrust",
    "Leg press",
]


def seed_builtin_exercises(db: Session) -> None:
    existing = set(db.scalars(select(Exercise.name).where(Exercise.user_id.is_(None))))
    for name in BUILTIN_EXERCISES:
        if name not in existing:
            db.add(Exercise(name=name, user_id=None))
    db.commit()
