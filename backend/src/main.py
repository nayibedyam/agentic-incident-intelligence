from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.database import close_db
from src.db.migrations import run_migrations
from src.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    yield
    await close_db()


app = FastAPI(
    title="Agentic Incident Intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
