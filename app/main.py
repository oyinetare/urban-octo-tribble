from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import auth, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core import init_db

    """
    Lifespan context manager for startup and shutdown events.

    Startup:
    - Initialize connections

    Shutdown:
    - Close connections
    """
    await init_db()

    yield


app = FastAPI(title="urban-octo-tribble API", version="1.0.0", lifespan=lifespan)

api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(documents.router, prefix=api_prefix)


@app.get("/")
def root():
    return {
        "message": "Welcome to urban-octo-tribble API",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
