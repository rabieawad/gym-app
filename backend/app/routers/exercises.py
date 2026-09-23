from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Exercise, User
from ..schemas import ExerciseIn, ExerciseOut

router = APIRouter(prefix="/api/exercises", tags=["exercises"])


def to_out(ex: Exercise) -> ExerciseOut:
    return ExerciseOut(id=ex.id, name=ex.name, custom=ex.user_id is not None)


def visible_exercises(user: User):
    """Built-in exercises plus the member's own."""
    return select(Exercise).where(or_(Exercise.user_id.is_(None), Exercise.user_id == user.id))


@router.get("", response_model=list[ExerciseOut])
def list_exercises(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(visible_exercises(user).order_by(func.lower(Exercise.name)))
    return [to_out(ex) for ex in rows]


@router.post("", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(
    data: ExerciseIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    clash = db.scalar(
        visible_exercises(user).where(func.lower(Exercise.name) == data.name.lower())
    )
    if clash:
        raise HTTPException(status.HTTP_409_CONFLICT, "That exercise already exists.")
    ex = Exercise(name=data.name, user_id=user.id)
    db.add(ex)
    db.commit()
    return to_out(ex)
