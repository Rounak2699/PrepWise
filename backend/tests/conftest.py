import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.main import app
from app.seed.seed import seed_questions


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    session = TestingSession()
    seed_questions(session)
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session, monkeypatch):
    # main.py's lifespan would create/seed against the real (file-based) engine;
    # skip it here since this fixture already has an isolated, pre-seeded session.
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register(client, email="student@example.com", password="password123", name="Test Student"):
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
