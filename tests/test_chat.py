import json
from unittest.mock import MagicMock, patch, mock_open

import httpx
import openai
import pytest

from backend.chat import Me


def _make_status_error(cls, status_code=429):
    """Create an openai APIStatusError subclass instance (RateLimitError, AuthenticationError)."""
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    resp = httpx.Response(status_code, request=req)
    return cls("error", response=resp, body={})


def _make_connection_error():
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return openai.APIConnectionError(request=req)


def _create_me(profile_text="Profile text", ref_text=None, summary_text="Summary text"):
    """Create a Me instance with all file I/O mocked."""

    def mock_pdf_reader(path):
        if "reference_letter" in path:
            if ref_text is None:
                raise FileNotFoundError("no reference letter")
            reader = MagicMock()
            page = MagicMock()
            page.extract_text.return_value = ref_text
            reader.pages = [page]
            return reader
        reader = MagicMock()
        page = MagicMock()
        page.extract_text.return_value = profile_text
        reader.pages = [page]
        return reader

    mock_openai = MagicMock()

    with patch("backend.chat.PdfReader", side_effect=mock_pdf_reader), \
         patch("builtins.open", mock_open(read_data=summary_text)), \
         patch("backend.chat.OpenAI", return_value=mock_openai):
        me = Me()

    return me


# ── __init__ ──────────────────────────────────────────────────

def test_init_loads_profile_text():
    me = _create_me(profile_text="My profile")
    assert me.profile == "My profile"


def test_init_loads_summary():
    me = _create_me(summary_text="My summary")
    assert me.summary == "My summary"


def test_init_loads_reference_letter():
    me = _create_me(ref_text="Great reference")
    assert me.ref_letter == "Great reference"


def test_init_missing_reference_letter_sets_empty_string():
    me = _create_me(ref_text=None)
    assert me.ref_letter == ""


def test_init_profile_extract_text_none_becomes_empty():
    """extract_text() returning None is handled by `or ""`."""
    def mock_pdf_reader(path):
        reader = MagicMock()
        page = MagicMock()
        page.extract_text.return_value = None
        reader.pages = [page]
        return reader

    with patch("backend.chat.PdfReader", side_effect=mock_pdf_reader), \
         patch("builtins.open", mock_open(read_data="")), \
         patch("backend.chat.OpenAI"):
        me = Me()

    assert me.profile == ""


# ── system_prompt ─────────────────────────────────────────────

def test_system_prompt_contains_name():
    me = _create_me()
    assert "Alex Rabinovich" in me.system_prompt()


def test_system_prompt_contains_summary():
    me = _create_me(summary_text="Unique summary XYZ")
    assert "Unique summary XYZ" in me.system_prompt()


def test_system_prompt_contains_profile():
    me = _create_me(profile_text="Unique profile ABC")
    assert "Unique profile ABC" in me.system_prompt()


def test_system_prompt_includes_reference_letter_section():
    me = _create_me(ref_text="Great reference letter")
    prompt = me.system_prompt()
    assert "## Reference Letter:" in prompt
    assert "Great reference letter" in prompt


def test_system_prompt_excludes_reference_section_when_absent():
    me = _create_me(ref_text=None)
    assert "## Reference Letter:" not in me.system_prompt()


def test_system_prompt_contains_scope_rule():
    me = _create_me()
    assert "STRICT SCOPE RULE" in me.system_prompt()


def test_system_prompt_contains_privacy_rule():
    me = _create_me()
    assert "PRIVACY RULE" in me.system_prompt()


# ── handle_tool_call ──────────────────────────────────────────

def test_handle_tool_call_record_user_details():
    me = _create_me()
    tool_call = MagicMock()
    tool_call.function.name = "record_user_details"
    tool_call.function.arguments = json.dumps({"email": "test@test.com", "name": "John"})
    tool_call.id = "call_123"

    with patch("backend.chat.record_user_details", return_value={"recorded": "ok"}) as mock_fn:
        results = me.handle_tool_call([tool_call])

    assert len(results) == 1
    assert results[0]["role"] == "tool"
    assert results[0]["tool_call_id"] == "call_123"
    assert json.loads(results[0]["content"]) == {"recorded": "ok"}
    mock_fn.assert_called_once_with(email="test@test.com", name="John")


def test_handle_tool_call_record_unknown_question():
    me = _create_me()
    tool_call = MagicMock()
    tool_call.function.name = "record_unknown_question"
    tool_call.function.arguments = json.dumps({"question": "What is 42?"})
    tool_call.id = "call_456"

    with patch("backend.chat.record_unknown_question", return_value={"recorded": "ok"}) as mock_fn:
        results = me.handle_tool_call([tool_call])

    assert len(results) == 1
    mock_fn.assert_called_once_with(question="What is 42?")


def test_handle_tool_call_unknown_tool_returns_empty_dict():
    me = _create_me()
    tool_call = MagicMock()
    tool_call.function.name = "nonexistent_tool"
    tool_call.function.arguments = json.dumps({})
    tool_call.id = "call_789"

    results = me.handle_tool_call([tool_call])

    assert len(results) == 1
    assert json.loads(results[0]["content"]) == {}


def test_handle_tool_call_multiple_calls():
    me = _create_me()
    t1 = MagicMock()
    t1.function.name = "record_user_details"
    t1.function.arguments = json.dumps({"email": "a@b.com"})
    t1.id = "c1"
    t2 = MagicMock()
    t2.function.name = "record_unknown_question"
    t2.function.arguments = json.dumps({"question": "Q?"})
    t2.id = "c2"

    with patch("backend.chat.record_user_details", return_value={"recorded": "ok"}), \
         patch("backend.chat.record_unknown_question", return_value={"recorded": "ok"}):
        results = me.handle_tool_call([t1, t2])

    assert len(results) == 2
    assert results[0]["tool_call_id"] == "c1"
    assert results[1]["tool_call_id"] == "c2"


# ── chat ──────────────────────────────────────────────────────

def _mock_response(content="Reply", finish_reason="stop"):
    resp = MagicMock()
    resp.choices[0].finish_reason = finish_reason
    resp.choices[0].message.content = content
    return resp


def test_chat_returns_model_reply():
    me = _create_me()
    me.openai.chat.completions.create.return_value = _mock_response("Hello!")
    assert me.chat("hi", []) == "Hello!"


def test_chat_includes_system_prompt_first():
    me = _create_me()
    me.openai.chat.completions.create.return_value = _mock_response()
    me.chat("hi", [])
    messages = me.openai.chat.completions.create.call_args[1]["messages"]
    assert messages[0]["role"] == "system"


def test_chat_appends_user_message_last():
    me = _create_me()
    me.openai.chat.completions.create.return_value = _mock_response()
    me.chat("my message", [])
    messages = me.openai.chat.completions.create.call_args[1]["messages"]
    assert messages[-1] == {"role": "user", "content": "my message"}


def test_chat_includes_history_between_system_and_user():
    me = _create_me()
    me.openai.chat.completions.create.return_value = _mock_response()
    history = [{"role": "user", "content": "prev"}, {"role": "assistant", "content": "ok"}]
    me.chat("new", history)
    messages = me.openai.chat.completions.create.call_args[1]["messages"]
    assert messages[1] == {"role": "user", "content": "prev"}
    assert messages[2] == {"role": "assistant", "content": "ok"}
    assert messages[3] == {"role": "user", "content": "new"}


def test_chat_handles_tool_calls_then_final_reply():
    me = _create_me()
    tool_call = MagicMock()
    tool_call.function.name = "record_unknown_question"
    tool_call.function.arguments = json.dumps({"question": "test?"})
    tool_call.id = "c1"

    tool_resp = MagicMock()
    tool_resp.choices[0].finish_reason = "tool_calls"
    tool_resp.choices[0].message.tool_calls = [tool_call]

    final_resp = _mock_response("Final answer")

    me.openai.chat.completions.create.side_effect = [tool_resp, final_resp]

    with patch("backend.chat.record_unknown_question", return_value={"recorded": "ok"}):
        result = me.chat("test?", [])

    assert result == "Final answer"
    assert me.openai.chat.completions.create.call_count == 2


def test_chat_rate_limit_returns_fallback_message():
    me = _create_me()
    me.openai.chat.completions.create.side_effect = _make_status_error(
        openai.RateLimitError, 429
    )
    with patch("backend.chat.push"):
        result = me.chat("hi", [])
    assert "unable to respond" in result.lower() or "rate limit" in result.lower()


def test_chat_rate_limit_calls_push():
    me = _create_me()
    me.openai.chat.completions.create.side_effect = _make_status_error(
        openai.RateLimitError, 429
    )
    with patch("backend.chat.push") as mock_push:
        me.chat("hi", [])
    mock_push.assert_called_once()
    assert "rate limit" in mock_push.call_args[0][0].lower()


def test_chat_authentication_error_returns_fallback():
    me = _create_me()
    me.openai.chat.completions.create.side_effect = _make_status_error(
        openai.AuthenticationError, 401
    )
    with patch("backend.chat.push"):
        result = me.chat("hi", [])
    assert "technical issue" in result.lower()


def test_chat_authentication_error_calls_push():
    me = _create_me()
    me.openai.chat.completions.create.side_effect = _make_status_error(
        openai.AuthenticationError, 401
    )
    with patch("backend.chat.push") as mock_push:
        me.chat("hi", [])
    mock_push.assert_called_once()
    assert "authentication" in mock_push.call_args[0][0].lower()


def test_chat_connection_error_returns_fallback():
    me = _create_me()
    me.openai.chat.completions.create.side_effect = _make_connection_error()
    with patch("backend.chat.push"):
        result = me.chat("hi", [])
    assert "connecting" in result.lower()


def test_chat_connection_error_calls_push():
    me = _create_me()
    me.openai.chat.completions.create.side_effect = _make_connection_error()
    with patch("backend.chat.push") as mock_push:
        me.chat("hi", [])
    mock_push.assert_called_once()
    assert "connection" in mock_push.call_args[0][0].lower()


def test_chat_generic_exception_returns_fallback():
    me = _create_me()
    me.openai.chat.completions.create.side_effect = ValueError("unexpected error")
    with patch("backend.chat.push"):
        result = me.chat("hi", [])
    assert "unexpected" in result.lower()


def test_chat_generic_exception_calls_push():
    me = _create_me()
    me.openai.chat.completions.create.side_effect = ValueError("boom")
    with patch("backend.chat.push") as mock_push:
        me.chat("hi", [])
    mock_push.assert_called_once()
    assert "ValueError" in mock_push.call_args[0][0]
