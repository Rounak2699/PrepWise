import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import auth, challenge, me, progress, reports
from .core.config import settings
from .core.db import Base, SessionLocal, engine
from .seed.seed import seed_questions

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In production, use Alembic migrations instead of create_all.
    Base.metadata.create_all(bind=engine)
    if settings.app_env != "production":
        with SessionLocal() as db:
            added = seed_questions(db)
            if added:
                logging.getLogger("startup").info("Seeded %d questions", added)
    yield


app = FastAPI(title="AI Placement Preparation Platform", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(me.router)
app.include_router(challenge.router)
app.include_router(progress.router)
app.include_router(reports.router)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}
