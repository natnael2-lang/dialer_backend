import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .config import MEDIA_DIR
from .database import Base, engine
from .routers import admin, auth, callers, calls, contacts, profiles


def migrate() -> None:
    """create_all() never alters existing tables, so add new columns by hand.
    Safe to run on every start (IF NOT EXISTS)."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS address VARCHAR(160)"))
        conn.execute(
            text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT TRUE")
        )
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    os.makedirs(MEDIA_DIR, exist_ok=True)
    Base.metadata.create_all(engine)
    migrate()
    yield


app = FastAPI(title="Dialer API", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(contacts.router)
app.include_router(callers.router)
app.include_router(calls.router)
app.include_router(admin.router)


# Photos have unique filenames, so they can be cached aggressively.
class ImmutableStatic(StaticFiles):
    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp


os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media", ImmutableStatic(directory=MEDIA_DIR), name="media")


@app.get("/health")
def health():
    return {"ok": True}
