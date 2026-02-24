import os
import re

import requests


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.lower())).strip()


def push(text: str) -> None:
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "title": "Digital Agent - Message",
            "message": text,
        },
    )


_recorded_emails: set[str] = set()


def record_user_details(email: str, name: str = "Name not provided", notes: str = "not provided") -> dict:
    key = email.strip().lower()
    if key in _recorded_emails:
        return {"recorded": "already_recorded"}
    _recorded_emails.add(key)
    push(f"Recording '{name}' with email '{email}' and notes '{notes}'")
    return {"recorded": "ok"}


_recorded_questions: set[str] = set()


def record_unknown_question(question: str) -> dict:
    key = _normalize(question)
    if key in _recorded_questions:
        return {"recorded": "already_recorded", "recorded_questions": list(_recorded_questions)}
    _recorded_questions.add(key)
    push(f"Recording '{question}' asked that I couldn't answer")
    return {"recorded": "ok", "recorded_questions": list(_recorded_questions)}


record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {"type": "string", "description": "The email address of this user"},
            "name": {"type": "string", "description": "The user's name, if they provided it"},
            "notes": {"type": "string", "description": "Any additional information about the conversation that's worth recording to give context"},
        },
        "required": ["email"],
        "additionalProperties": False,
    },
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question you didn't answer — whether because you didn't know the answer, or because it was outside the professional scope. Before calling, check if a semantically equivalent question already appears in the `recorded_questions` list from a prior call response. If so, skip this call.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question that couldn't be answered"},
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}

tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": record_unknown_question_json},
]
