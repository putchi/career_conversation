import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.chat import Me
from backend.models import ChatRequest, ChatResponse

load_dotenv(override=True)

port = int(os.environ.get("PORT", 8000))

me: Me | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global me
    me = Me()
    yield


app = FastAPI(title="Alex Rabinovich Digital Twin", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in request.history]
    reply = me.chat(request.message, history)
    return ChatResponse(reply=reply)


# Mount frontend — must be last (catch-all)
dist = Path(__file__).parent.parent / "frontend" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=str(dist), html=True), name="static")
