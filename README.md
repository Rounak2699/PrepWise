# Prepwise — AI Placement Preparation Platform

A daily-practice app for pre-final and final-year students preparing for campus
placements: a 10–15 question aptitude + core-CS test every day, instant scoring,
topic-level progress tracking, streaks, and an AI-generated performance report
after every test.

Built from the project's Master Documentation (PRD + SRS v1.0).

## Stack

- **Backend:** FastAPI, SQLAlchemy 2, SQLite (dev) / PostgreSQL (prod), JWT auth
- **Frontend:** React 19 + Vite, Tailwind CSS v4, React Router, Recharts
- **AI report:** Claude (via the Anthropic API) — optional; the app works fully
  without an API key, falling back to a template-based summary

## Quick start (Docker)

```bash
cp backend/.env.example backend/.env
# edit backend/.env and set a real JWT_SECRET; add ANTHROPIC_API_KEY if you want AI reports

docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000 (docs at `/docs`)

The database schema is created automatically on first boot. In dev mode
(`APP_ENV=development`, the default), the question bank is also seeded
automatically so you have something to test with right away.

## Quick start (manual, for local development)

**Backend**

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

This runs on SQLite by default (`placement.db`, created automatically) — no
Postgres needed for local dev. Runs on http://localhost:8000.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Runs on http://localhost:5173 and proxies `/api/*` to `http://localhost:8000`
(see `vite.config.js`) — no `.env` needed for local dev.

## Running the backend tests

```bash
cd backend
source venv/bin/activate
pytest
```

26 tests covering auth, onboarding validation, the full daily-challenge
lifecycle (start → answer → submit → idempotent resubmission → result →
report → progress/streaks), ownership checks, and AI-provider failure modes
(missing key, provider exception, malformed response all degrade to a
template report rather than breaking the test flow).

There's also `backend/smoke_test.py`, a standalone script that exercises the
same flow against a **live** running server (not a mock) — useful as a quick
manual sanity check after infra changes:

```bash
uvicorn app.main:app --port 8123 &
python smoke_test.py
```

## Project structure

```
backend/
  app/
    core/        config, db session, JWT/password hashing, clock (timezone-aware "today")
    api/         route handlers (auth, profile, daily challenge/test engine, progress, reports)
    services/    challenge generation, scoring/evaluation, AI narrative, report assembly
    seed/        starter question bank (63 questions across 9 topics) + seeding script
    models.py    SQLAlchemy models
    schemas.py   Pydantic request/response schemas
    taxonomy.py  category/topic labels shared across the app
  tests/         pytest suite
frontend/
  src/
    pages/       Login, Register, Onboarding, Dashboard, TakeTest, Result, Progress, Profile
    components/  shared UI (Button, Card, AppShell/nav, route guards)
    context/     auth context (JWT storage, current user)
    lib/         API client, topic/category label helpers
docker-compose.yml   postgres + backend + frontend(nginx), for a production-like run
```

## How the daily challenge works

- One test per user per calendar day, in the user's configured timezone
  (`APP_TIMEZONE`, default `Asia/Kolkata`).
- Question selection is **deterministic per user per day** (seeded by
  `user_id + date`) but weighted toward the user's weaker topics and stated
  preferences, so refreshing the page doesn't reshuffle an in-progress test.
- A test has a time limit (default: 75s × question count). The timer is
  tracked server-side (`started_at` + `duration_seconds`); if a test is
  fetched after time has expired, it's auto-submitted with whatever was
  answered.
- Scoring, streaks, and topic performance are computed deterministically in
  `services/evaluation.py` — the AI is never in the scoring path. It only
  writes a narrative summary (`services/ai.py` → `services/report.py`) on top
  of numbers that are already final. If the AI call fails or no API key is
  configured, a template-based summary is used instead — the test result
  itself is never blocked on it.

## Known limitations / suggested next steps

This covers the MVP scope from the PRD (auth, onboarding, daily aptitude +
core-CS MCQ test, scoring, streaks, topic progress, AI report). Not yet
built, per the doc's later-phase items:

- **Coding-round practice** (sandboxed judge) — deferred; `type` on
  `Question` already supports adding a `"coding"` type later without a schema
  change.
- **Schema migrations** — the app currently uses
  `Base.metadata.create_all()` on startup, which is fine for this stage but
  doesn't handle evolving an existing production schema. Introduce Alembic
  before making structural model changes against a live database.
- **Auth token storage** — the frontend stores the JWT in `localStorage` for
  simplicity. For production hardening, move to an httpOnly cookie issued by
  the backend to reduce XSS exposure.
- **Admin/content-management screens** — question authoring is currently
  file-based (`app/seed/questions.py`); there's no admin UI to add/edit
  questions yet.
- **Rate limiting** — the AI report call has a timeout but no per-user rate
  limit; add one if this goes multi-tenant with a shared Anthropic budget.
