# Ironhouse — gym website (app code only)

A small, extendable web app: a public landing page plus member accounts with a training log
(log lifts, see history, see a progress chart per exercise).

No Docker, CI/CD or server config is included on purpose — that part is yours.

## Stack

| Part | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic v2 |
| Auth | bcrypt password hashes, JWT bearer tokens (PyJWT) |
| Database | SQLite by default; any SQLAlchemy URL works (Postgres later) |
| Frontend | Plain HTML/CSS/JS — no build step, no npm. Served by the backend. |

## Run it locally

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env           # optional for local dev
uvicorn app.main:app --reload  # http://localhost:8000
```

- Site: `http://localhost:8000/`
- API docs (Swagger): `http://localhost:8000/api/docs`
- Tests: `pip install -r requirements-dev.txt && pytest`

The backend creates its tables and seeds the built-in exercises on startup.

## Things you'll care about as DevOps

- **One process, one port.** `uvicorn app.main:app --host 0.0.0.0 --port 8000` serves both the API (`/api/*`)
  and the static frontend (`../frontend`, or wherever `FRONTEND_DIR` points). You can also put the
  frontend behind nginx/Caddy and set `FRONTEND_DIR=` (empty) to run the API only. The frontend calls
  the API with relative URLs (`/api/...`), so route `/api` to the backend from the same origin.
- **Health check:** `GET /api/health` → `200 {"status":"ok"}`, or `503` if the database is unreachable.
- **Config is 100% environment variables** (see `backend/.env.example`):
  `SECRET_KEY`, `ENVIRONMENT`, `DATABASE_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `FRONTEND_DIR`, `CORS_ORIGINS`.
  With `ENVIRONMENT=production` the app refuses to start unless `SECRET_KEY` is changed.
- **Data:** the SQLite file lives at `backend/data/gym.db` by default (set `DATABASE_URL` to move it).
  That file is the only state — back it up.
- **Dependencies are pinned** in `requirements.txt`; `requirements-dev.txt` adds pytest for your CI.
- **No rate limiting** in the app. Add it at the reverse proxy (especially `/api/auth/*`).
- **Schema changes:** tables are created with `create_all()`, which doesn't alter existing tables.
  Once you start changing existing tables in later features, add Alembic migrations.

## Project layout

```
backend/
  app/
    main.py          app setup, startup, static file serving
    config.py        environment-based settings
    database.py      engine / session
    models.py        tables: User, Exercise, LiftEntry
    schemas.py       request/response validation
    security.py      password hashing + JWT
    deps.py          get_current_user dependency
    seed.py          built-in exercises
    routers/         one file per feature area
  tests/             pytest API tests
frontend/
  index.html         public landing page
  login.html         log in / create account
  dashboard.html     the member's training log
  css/style.css
  js/api.js          API client + tiny DOM helper
  js/login.js, js/dashboard.js
```

## API overview

| Method | Path | Notes |
|---|---|---|
| GET | `/api/health` | liveness + DB check |
| POST | `/api/auth/register` | `{email, display_name, password}` → token + user |
| POST | `/api/auth/login` | `{email, password}` → token + user |
| GET | `/api/auth/me` | current user |
| GET / POST | `/api/exercises` | built-ins plus the member's own |
| GET / POST | `/api/lifts` | list (newest first, `?exercise_id=`) / log a lift |
| GET | `/api/lifts/progress?exercise_id=` | per-day best weight and estimated 1RM |
| DELETE | `/api/lifts/{id}` | delete one of your own lifts |

Everything except `health`, `register` and `login` needs `Authorization: Bearer <token>`.
Members can only ever see and change their own data.

## Adding a feature later

1. Add a model in `models.py` (give it a `user_id` foreign key so it belongs to a member).
2. Add request/response schemas in `schemas.py`.
3. Create `app/routers/<feature>.py` using `Depends(get_current_user)`, and add it to the list
   in `app/routers/__init__.py`.
4. Add tests in `tests/`.
5. On the frontend, add a section to `dashboard.html` (or a new page) and call the API with `Api.get/post/del`.

Ideas that fit the current design: workout sessions grouping several lifts, body weight tracking,
class bookings, membership status, an admin role, password reset by email.

## Known limits of this first version

- The token is stored in `localStorage` (simple, fine for this app; an httpOnly cookie is the stricter option).
- No email verification, password reset or admin area yet.
- Weights are in kg only.
- The gym name, hours and prices on the landing page are placeholders — edit `frontend/index.html`
  (and the `<title>`/brand text on the other pages).
