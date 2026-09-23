from collections import defaultdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user
from ..models import Exercise, LiftEntry, User
from ..schemas import LiftIn, LiftOut, ProgressOut, ProgressPoint
from .exercises import to_out as exercise_out
from .exercises import visible_exercises

router = APIRouter(prefix="/api/lifts", tags=["lifts"])


def _lift_out(lift: LiftEntry) -> LiftOut:
    return LiftOut(
        id=lift.id,
        exercise_id=lift.exercise_id,
        exercise_name=lift.exercise.name,
        weight_kg=lift.weight_kg,
        reps=lift.reps,
        sets=lift.sets,
        performed_on=lift.performed_on,
        notes=lift.notes,
    )


def _epley_1rm(weight: float, reps: int) -> float:
    """Estimated one-rep max (Epley formula)."""
    return weight if reps == 1 else weight * (1 + reps / 30)


def _get_visible_exercise(db: Session, user: User, exercise_id: int) -> Exercise:
    ex = db.scalar(visible_exercises(user).where(Exercise.id == exercise_id))
    if ex is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exercise not found.")
    return ex


@router.get("", response_model=list[LiftOut])
def list_lifts(
    exercise_id: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(LiftEntry)
        .options(joinedload(LiftEntry.exercise))
        .where(LiftEntry.user_id == user.id)
        .order_by(LiftEntry.performed_on.desc(), LiftEntry.id.desc())
        .limit(limit)
    )
    if exercise_id is not None:
        stmt = stmt.where(LiftEntry.exercise_id == exercise_id)
    return [_lift_out(lift) for lift in db.scalars(stmt)]


@router.post("", response_model=LiftOut, status_code=status.HTTP_201_CREATED)
def create_lift(data: LiftIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_visible_exercise(db, user, data.exercise_id)
    lift = LiftEntry(
        user_id=user.id,
        exercise_id=data.exercise_id,
        weight_kg=data.weight_kg,
        reps=data.reps,
        sets=data.sets,
        performed_on=data.performed_on or date.today(),
        notes=data.notes,
    )
    db.add(lift)
    db.commit()
    db.refresh(lift)
    return _lift_out(lift)


@router.get("/progress", response_model=ProgressOut)
def progress(
    exercise_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Per-day best weight and estimated 1RM for one exercise, oldest first."""
    exercise = _get_visible_exercise(db, user, exercise_id)
    lifts = db.scalars(
        select(LiftEntry).where(LiftEntry.user_id == user.id, LiftEntry.exercise_id == exercise_id)
    ).all()

    by_day: dict[date, list[LiftEntry]] = defaultdict(list)
    for lift in lifts:
        by_day[lift.performed_on].append(lift)

    points = [
        ProgressPoint(
            date=day,
            top_weight_kg=max(l.weight_kg for l in entries),
            est_1rm_kg=round(max(_epley_1rm(l.weight_kg, l.reps) for l in entries), 1),
        )
        for day, entries in sorted(by_day.items())
    ]
    best = max(points, key=lambda p: (p.top_weight_kg, -p.date.toordinal()), default=None)
    return ProgressOut(
        exercise=exercise_out(exercise),
        points=points,
        best_weight_kg=best.top_weight_kg if best else None,
        best_weight_date=best.date if best else None,
        best_est_1rm_kg=max((p.est_1rm_kg for p in points), default=None),
    )


@router.delete("/{lift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lift(lift_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lift = db.scalar(select(LiftEntry).where(LiftEntry.id == lift_id, LiftEntry.user_id == user.id))
    if lift is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lift not found.")
    db.delete(lift)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
