import os
from dotenv import load_dotenv
import pathlib
load_dotenv(pathlib.Path(__file__).parent.parent.parent / '.env')

from fastapi import FastAPI

from app.routes.chats import router as chats_router
from app.routes.health import router as health_router
from app.routes.screen import router as screen_router

app = FastAPI(title="MatAgent-Critique API", version="0.1.0")
app.include_router(health_router)
app.include_router(chats_router)
app.include_router(screen_router)
