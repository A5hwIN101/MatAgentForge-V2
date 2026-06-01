import os
from dotenv import load_dotenv
import pathlib
load_dotenv(pathlib.Path(__file__).parent.parent.parent / '.env')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.chats import router as chats_router
from app.routes.feedback import router as feedback_router
from app.routes.health import router as health_router
from app.routes.screen import router as screen_router

default_origins = {
    "http://localhost:3000",
    "http://localhost:3001",
    "https://mat-agent-forge-v2.vercel.app",
}
frontend_origin = os.getenv("FRONTEND_ORIGIN", "").strip()
if frontend_origin:
    default_origins.add(frontend_origin.rstrip("/"))

app = FastAPI(title="MatAgent-Critique API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(default_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(chats_router)
app.include_router(feedback_router)
app.include_router(screen_router)
