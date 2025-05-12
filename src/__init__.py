from fastapi import FastAPI
from src.db.models import init_db
from src.routes.default import router as default_router
from src.routes.games import router as games_router
from src.routes.users import router as user_router
from contextlib import asynccontextmanager
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from env import DOMAIN


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server is starting...")
    init_db()
    yield
    print("Server is stopping...")


version = "v1"
app = FastAPI(title="learn your language api", version=version, lifespan=lifespan)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", DOMAIN])

app.include_router(default_router)
app.include_router(router=games_router, prefix=f"/api/{version}/games")
app.include_router(router=user_router, prefix=f"/api/{version}/users")