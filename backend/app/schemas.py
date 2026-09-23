"""Request and response shapes (validated by Pydantic)."""
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---- auth -------------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("display_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name can't be empty.")
        return v

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password is too long (72 bytes maximum).")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- exercises --------------------------------------------------------------
class ExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Name can't be empty.")
        return v


class ExerciseOut(BaseModel):
    id: int
    name: str
    custom: bool


# ---- lifts ------------------------------------------------------------------
class LiftIn(BaseModel):
    exercise_id: int
    weight_kg: float = Field(gt=0, le=1000)
    reps: int = Field(ge=1, le=200)
    sets: int = Field(default=1, ge=1, le=50)
    performed_on: date | None = None  # defaults to today
    notes: str = Field(default="", max_length=300)

    @field_validator("notes")
    @classmethod
    def _strip_notes(cls, v: str) -> str:
        return v.strip()


class LiftOut(BaseModel):
    id: int
    exercise_id: int
    exercise_name: str
    weight_kg: float
    reps: int
    sets: int
    performed_on: date
    notes: str


class ProgressPoint(BaseModel):
    date: date
    top_weight_kg: float
    est_1rm_kg: float


class ProgressOut(BaseModel):
    exercise: ExerciseOut
    points: list[ProgressPoint]
    best_weight_kg: float | None
    best_weight_date: date | None
    best_est_1rm_kg: float | None
