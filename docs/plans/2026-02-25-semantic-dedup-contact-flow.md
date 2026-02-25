# Plan: Semantic Question Dedup + Improved Contact Flow

## Context

Two improvements to the career chatbot's notification and conversation handling:

1. **Semantic dedup for unknown questions** — The existing text-normalization dedup misses rephrased equivalents (e.g. "Do you know Bill Gates?" vs "Are you friends with Bill Gates?"). Add a new `check_question_similarity` tool so the main LLM can explicitly verify similarity before deciding whether to call `record_unknown_question`. The similarity check itself uses a secondary LLM call.

2. **Contact flow improvements** — The system prompt passively says "try to steer them towards getting in touch via email." This needs to be explicit: when a user expresses interest in reaching out, the bot should ask for name + email AND mention LinkedIn in the same breath, and must not call the tool until the user actually provides an email. Dedup is per email address — the same email triggers no second notification. If the user submits a **different** email (e.g., correcting a typo), the bot must ask the user to confirm before calling the tool again, and an LLM-based guardrail in the tool checks whether the new submission looks like legitimate correction or abuse before recording. After recording, the bot's response should confirm Alex will be in touch AND remind the user they can reach out via LinkedIn at any time.

---

## Feature 1: Explicit Similarity Tool + Secondary LLM Check

### Architecture

```
User message
   |
   v
Main LLM
   | calls check_question_similarity(question)
   v
tool fn → _is_semantically_similar() → secondary LLM call (gpt-4.1-mini)
             |
             v
         {"question": "...", "already_recorded": true/false}
             |
             v
Main LLM: if already_recorded=true → skip record_unknown_question, acknowledge repeat
          if already_recorded=false → calls record_unknown_question(question)
                    |
                    v
              Pushover notification + reply to user
```

`check_question_similarity` only reads state — no recording, no notification.
`record_unknown_question` only records and notifies — no similarity check needed (the LLM already checked).

---

### Changes to `backend/tools.py`

**1. New imports** (top of file, after existing imports):
```python
import json
from openai import OpenAI
```

**2. New module-level state** (after existing imports, before `_normalize`):
```python
_openai_client: OpenAI | None = None
_recorded_questions_raw: list[str] = []
```

**3. `set_openai_client` function** (after module-level vars):
```python
def set_openai_client(client: OpenAI) -> None:
    global _openai_client
    _openai_client = client
```

**4. `_is_semantically_similar` private helper** (before `check_question_similarity`):

Loops through each recorded question **one at a time**, making one focused LLM call per pair. Short-circuits on the first match. Only returns `False` after every recorded question has been checked without a match.

```python
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
```

- Loops through **all** recorded questions until either a match is found or the list is exhausted.
- Per-call error: `continue` to the next question (skip that comparison rather than failing entirely).
- If `_openai_client is None`: returns `False` immediately — no crash, text-norm check already ran.

**Note on asyncio:** The checks run sequentially (one LLM call per recorded question). Parallel execution with `asyncio.gather` would save latency but would require refactoring the entire chat loop to async. For this chatbot's scale (typically <15 recorded questions in a session), sequential sync is fine and consistent with the rest of the codebase. This can be revisited if latency becomes an issue.

**5. New `check_question_similarity` function** (after `_is_semantically_similar`):
```python
def check_question_similarity(question: str) -> dict:
    key = _normalize(question)
    if key in _recorded_questions:
        return {"question": question, "already_recorded": True}
    if _is_semantically_similar(question, _recorded_questions_raw):
        return {"question": question, "already_recorded": True}
    return {"question": question, "already_recorded": False}
```

Text normalization runs first (fast, free). LLM check only runs if no text match (~80 input tokens, ~$0.00003 per call).

**6. Update `record_unknown_question`** — append to `_recorded_questions_raw` on new recording (lines 38–44):
```python
def record_unknown_question(question: str) -> dict:
    key = _normalize(question)
    if key in _recorded_questions:
        return {"recorded": "already_recorded", "recorded_questions": list(_recorded_questions)}
    _recorded_questions.add(key)
    _recorded_questions_raw.append(question)
    push(f"Recording '{question}' asked that I couldn't answer")
    return {"recorded": "ok", "recorded_questions": list(_recorded_questions)}
```

No semantic check here — the LLM already called `check_question_similarity`. Text-norm check kept as a safety net.

**Also add `_is_contact_suspicious` private helper** (before `record_user_details`):

Called only when a second (different) email is submitted in the same session. Returns `True` if the submission looks like abuse. Hard limit of 3+ recorded emails bypasses the LLM call entirely.

```python
def _is_contact_suspicious(new_email: str, existing_emails: list[str]) -> bool:
    if len(existing_emails) >= 3:
        return True  # Hard limit — no LLM call needed
    if _openai_client is None:
        return False
    prompt = (
        f"A chatbot has already recorded these email addresses in this session: {existing_emails}\n"
        f"The user is now submitting a different email: {new_email}\n\n"
        "Does this look like legitimate use (e.g., correcting a typo, updating their email) "
        "or potential abuse/spam (e.g., submitting many unrelated emails)?"
    )
    try:
        resp = _openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": 'You are an abuse detection classifier. Respond with JSON only: {"suspicious": true} or {"suspicious": false}.',
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=10,
            temperature=0,
        )
        return json.loads(resp.choices[0].message.content.strip()).get("suspicious", False)
    except Exception:
        return False  # Fail open — don't block legitimate users on error
```

**Also update `record_user_details`** — dedup per email; if a different email is submitted and passes the abuse check, record and notify:

```python
def record_user_details(email: str, name: str = "Name not provided", notes: str = "not provided") -> dict:
    key = email.strip().lower()
    if key in _recorded_emails:
        return {"recorded": "already_recorded"}
    if _recorded_emails and _is_contact_suspicious(key, list(_recorded_emails)):
        return {"recorded": "suspicious"}
    _recorded_emails.add(key)
    push(f"Recording '{name}' with email '{email}' and notes '{notes}'")
    return {"recorded": "ok"}
```

Same email → `already_recorded`. Different email when no prior emails → record normally. Different email when prior emails exist → LLM abuse check first; if suspicious → return `"suspicious"`, else record and notify.

**7. New `check_question_similarity_json` tool definition** (after `record_unknown_question_json`):
```python
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
```

**8. Update `tools` list** (line 75–78):
```python
tools = [
    {"type": "function", "function": record_user_details_json},
    {"type": "function", "function": check_question_similarity_json},
    {"type": "function", "function": record_unknown_question_json},
]
```

---

### Changes to `backend/chat.py`

**Line 10** — add `set_openai_client` and `check_question_similarity` to import:
```python
from backend.tools import push, record_user_details, record_unknown_question, tools, set_openai_client, check_question_similarity
```

**`Me.__init__`** — inject client immediately after `self.openai = OpenAI()` (line 18):
```python
def __init__(self) -> None:
    self.openai = OpenAI()
    set_openai_client(self.openai)
    project_id = os.environ.get("SANITY_PROJECT_ID")
    ...
```

**`handle_tool_call`** — add `check_question_similarity` to the dispatch map (line 161):
```python
tool_fn = {
    "record_user_details": record_user_details,
    "record_unknown_question": record_unknown_question,
    "check_question_similarity": check_question_similarity,
}.get(tool_name)
```

---

## Feature 2: Contact Flow — System Prompt Update

**`backend/chat.py`** — replace `tool_instructions` string (lines 108–131).

Key changes from current text:
- Sequence made explicit: call `check_question_similarity` FIRST, then decide on `record_unknown_question`
- Contact trigger changed from "if the user is engaging, try to steer" → "when user expresses interest in contacting..."
- LinkedIn mentioned proactively in the contact invitation (currently only in `privacy` as a defensive fallback)
- Explicit guard: "do NOT call `record_user_details` until user has provided an email address"
- `{self.linkedin_url}` used (dynamic), not hardcoded

```python
tool_instructions = (
    "For any question you cannot answer — whether on-topic but unknown, or outside the professional scope — "
    "you MUST first call check_question_similarity, then act on its result: "
    "if already_recorded is true, skip record_unknown_question and acknowledge the repeat "
    "(e.g. 'It looks like you already asked something similar — I've already noted it. "
    "Would you like to rephrase or clarify?'); "
    "if already_recorded is false, call record_unknown_question before sending your response. "
    f"When a user expresses interest in contacting {self.name} or working together: "
    "warmly invite them to share their name and email, and mention LinkedIn as an easy alternative in the same breath "
    f"(e.g. 'Feel free to drop your email here — or connect directly via LinkedIn: {self.linkedin_url}'). "
    "Do NOT call record_user_details until the user has actually provided an email address. "
    "Once they provide their email, call record_user_details exactly once per conversation. "
    "After recording, confirm warmly and briefly — like a confident personal assistant — "
    f"that their details are noted and {self.name} will be in touch, and remind them they can also reach out via LinkedIn at any time. "
    "Do NOT explain that you don't send emails yourself or add unnecessary disclaimers. "
    f"Example: 'Thanks! {self.name} has been notified and will try to get in touch with you soon. "
    f"You can also reach out directly via LinkedIn at any time: {self.linkedin_url}' "
    "If the conversation history already contains an assistant message acknowledging that contact details were recorded "
    "and the user provides the SAME email again, tell them their details are already on file. "
    "If the user provides a DIFFERENT email after contact details have already been recorded, "
    "ask them to confirm before calling record_user_details again "
    f"(e.g. 'I see I already have your contact details on file — would you like me to also pass on this new email to {self.name}?'). "
    "Only call record_user_details a second time after the user explicitly confirms. "
    'If record_user_details returns {"recorded": "already_recorded"}, say: '
    f"'Looks like your details are already on file — {self.name} will be in touch! "
    f"Feel free to connect on LinkedIn too: {self.linkedin_url}' "
    'If record_user_details returns {"recorded": "suspicious"}, politely decline: '
    f"'I'm not able to record additional contact details at this time. "
    f"Please reach out directly via LinkedIn: {self.linkedin_url}'"
)
```

---

## Implementation Steps

1. Save this plan to `docs/plans/2026-02-25-semantic-dedup-contact-flow.md`
2. Edit `backend/tools.py` — all additions in order: imports, module-level state, `set_openai_client`, `_is_semantically_similar`, `check_question_similarity`, update `record_unknown_question`, add `_is_contact_suspicious`, update `record_user_details`, new tool JSON, update `tools` list
3. Edit `backend/chat.py` — update import, inject client in `__init__`, add to `handle_tool_call` dispatch, replace `tool_instructions`
4. Verify manually (see Verification section)

---

## Critical Files

- `backend/tools.py` — new tool function + helper, client injection, state tracking
- `backend/chat.py` — client injection, tool dispatch map, system prompt

---

## Verification

1. **Semantic dedup — rephrasing**: Send an unanswerable question (e.g. "What is Alex's shoe size?"). Confirm Pushover fires once. Then send "Do you know what shoe size Alex wears?" — should get `already_recorded` response from `check_question_similarity`, no second notification.

2. **Semantic dedup — unrelated**: Send "Do you know Bill Gates?" then "What is your favourite food?" — both should fire Pushover (different topics).

3. **Text dedup still works**: Send exact same question twice — second should be caught by normalization in `check_question_similarity`, no second notification.

4. **Contact flow — invitation**: Say "I'd love to get in touch with you" — bot should respond with invitation for name/email AND mention LinkedIn, without calling any tool yet.

5. **Contact flow — recording**: Provide name + email — bot calls `record_user_details`, Pushover fires once, bot confirms warmly with LinkedIn mention in the reply.

6. **Contact dedup — same email**: Submit same email again in same session — `already_recorded` response, no second Pushover. Response includes LinkedIn reminder.

7. **Contact dedup — different email (legitimate)**: After recording email A, provide email B. Bot should ask to confirm before calling the tool. After user confirms, `_is_contact_suspicious` passes (only one prior email, looks like a correction), Pushover fires, bot confirms warmly.

8. **Contact dedup — abuse**: After recording two emails, submit a third unrelated email. Either the hard limit (`len >= 3`) or the LLM abuse check fires, `record_user_details` returns `{"recorded": "suspicious"}`, bot declines politely and directs to LinkedIn.

9. **Client injection path**: Both Sanity and file-fallback paths call `set_openai_client` (it's the first line of `__init__` before the branch), so semantic check works in both environments.
