import json
import os
import re
from dataclasses import dataclass, field as _field

import requests
from openai import OpenAI


_openai_client: OpenAI | None = None
_recorded_questions_raw: list[str] = []


def set_openai_client(client: OpenAI) -> None:
    global _openai_client
    _openai_client = client


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


@dataclass
class _SessionState:
    notification_sent: bool = False
    recorded_email: str = ""
    email_change_count: int = 0
    override_used: bool = False


_session_states: dict[str, _SessionState] = {}
_current_session_id: str = ""


def set_session_id(session_id: str) -> None:
    global _current_session_id
    _current_session_id = session_id


def record_user_details(
    email: str,
    name: str = "Name not provided",
    notes: str = "not provided",
    override: bool = False,
) -> dict:
    key = email.strip().lower()
    state = _session_states.setdefault(_current_session_id, _SessionState())

    # Rule 5: explicit override resets notification state (once per session)
    if override:
        if state.override_used:
            return {"recorded": "already_overridden"}
        state.notification_sent = False
        state.override_used = True

    # Rules 1-3: dedup by notification_sent flag
    if state.notification_sent:
        if key == state.recorded_email:
            return {"recorded": "already_recorded"}  # Rule 1
        state.email_change_count += 1
        if state.email_change_count > 1:
            return {"recorded": "suspicious"}  # Rule 3
        state.recorded_email = key
        return {"recorded": "corrected"}  # Rule 2

    # First notification for this session
    push(f"Recording '{name}' with email '{email}' and notes '{notes}'")
    state.notification_sent = True
    state.recorded_email = key
    return {"recorded": "ok"}


_recorded_questions: set[str] = set()


def _is_semantically_similar(question: str, existing: list[str]) -> bool:
    if not existing or _openai_client is None:
        return False
    for recorded_q in existing:
        prompt = (
            f"Question A: {recorded_q}\n"
            f"Question B: {question}\n\n"
            "Are these two questions semantically equivalent — meaning they ask for the same information, "
            "even if worded differently?"
        )
        try:
            resp = _openai_client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {
                        "role": "system",
                        "content": 'You are a semantic similarity classifier. Respond with JSON only: {"similar": true} or {"similar": false}.',
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=10,
                temperature=0,
            )
            if json.loads(resp.choices[0].message.content.strip()).get("similar", False):
                return True
        except Exception:
            continue  # skip this comparison on error, try next recorded question
    return False


def check_question_similarity(question: str) -> dict:
    key = _normalize(question)
    if key in _recorded_questions:
        return {"question": question, "already_recorded": True}
    if _is_semantically_similar(question, _recorded_questions_raw):
        return {"question": question, "already_recorded": True}
    return {"question": question, "already_recorded": False}


def record_unknown_question(question: str) -> dict:
    key = _normalize(question)
    if key in _recorded_questions:
        return {"recorded": "already_recorded", "recorded_questions": list(_recorded_questions)}
    _recorded_questions.add(key)
    _recorded_questions_raw.append(question)
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
            "override": {
                "type": "boolean",
                "description": "Set to true ONLY when the user explicitly asks to replace a previously provided email (e.g. 'please ignore my previous email and use this one'). Never set for first-time recordings.",
            },
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

check_question_similarity_json = {
    "name": "check_question_similarity",
    "description": (
        "Call this tool BEFORE record_unknown_question to check whether a semantically equivalent question "
        "has already been recorded. Returns {\"already_recorded\": true} if the question is a duplicate "
        "(including rephrasing or synonyms). If already_recorded is true, skip record_unknown_question."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question to check for similarity"},
        },
        "required": ["question"],
        "additionalProperties": False,
    },
}

tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": check_question_similarity_json},
    {"type": "function", "function": record_unknown_question_json},
]
