from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []
    session_id: str = ""


class ChatResponse(BaseModel):
    reply: str
