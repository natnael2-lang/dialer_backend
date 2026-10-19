import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import MEDIA_DIR
from .database import Base, engine
from .routers import contacts, profiles


@asynccontextmanager
async def lifespan(_: FastAPI):
    os.makedirs(MEDIA_DIR, exist_ok=True)
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Dialer API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(profiles.router)
app.include_router(contacts.router)

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
