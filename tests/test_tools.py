import pytest
from unittest.mock import patch

from backend.tools import (
    push, record_user_details, record_unknown_question, tools,
    set_session_id, _session_states, _recorded_questions, _recorded_questions_raw,
)


@pytest.fixture(autouse=True)
def reset_state():
    _session_states.clear()
    _recorded_questions.clear()
    _recorded_questions_raw.clear()
    set_session_id("test-session")
    yield
    _session_states.clear()
    _recorded_questions.clear()
    _recorded_questions_raw.clear()
    set_session_id("")


# --- push tests ---

def test_push_sends_post_to_pushover():
    with patch("backend.tools.requests.post") as mock_post:
        push("test message")
    mock_post.assert_called_once()
    url = mock_post.call_args[0][0]
    assert url == "https://api.pushover.net/1/messages.json"


def test_push_includes_message_in_payload():
    with patch("backend.tools.requests.post") as mock_post:
        push("hello world")
    data = mock_post.call_args[1]["data"]
    assert data["message"] == "hello world"


def test_push_reads_tokens_from_env(monkeypatch):
    monkeypatch.setenv("PUSHOVER_TOKEN", "tok123")
    monkeypatch.setenv("PUSHOVER_USER", "usr456")
    with patch("backend.tools.requests.post") as mock_post:
        push("msg")
    data = mock_post.call_args[1]["data"]
    assert data["token"] == "tok123"
    assert data["user"] == "usr456"


# --- record_user_details: rule 1 (single notification) ---

def test_record_user_details_returns_ok():
    with patch("backend.tools.push"):
        result = record_user_details(email="a@b.com", name="Alice", notes="interested")
    assert result == {"recorded": "ok"}


def test_record_user_details_calls_push_with_email():
    with patch("backend.tools.push") as mock_push:
        record_user_details(email="a@b.com", name="Alice", notes="notes")
    mock_push.assert_called_once()
    assert "a@b.com" in mock_push.call_args[0][0]


def test_record_user_details_uses_defaults():
    with patch("backend.tools.push") as mock_push:
        result = record_user_details(email="a@b.com")
    assert result == {"recorded": "ok"}
    assert "Name not provided" in mock_push.call_args[0][0]


def test_record_user_details_same_email_second_call_returns_already_recorded():
    with patch("backend.tools.push"):
        record_user_details(email="a@b.com")
        result = record_user_details(email="a@b.com")
    assert result == {"recorded": "already_recorded"}


def test_record_user_details_same_email_no_second_push():
    with patch("backend.tools.push") as mock_push:
        record_user_details(email="a@b.com")
        record_user_details(email="a@b.com")
    assert mock_push.call_count == 1


# --- rule 2 (email correction) ---

def test_record_user_details_corrected_email_returns_corrected():
    with patch("backend.tools.push"):
        record_user_details(email="a@b.com")
        result = record_user_details(email="typo-fixed@b.com")
    assert result == {"recorded": "corrected"}


def test_record_user_details_corrected_email_no_second_push():
    with patch("backend.tools.push") as mock_push:
        record_user_details(email="a@b.com")
        record_user_details(email="typo-fixed@b.com")
    assert mock_push.call_count == 1


# --- rule 3 (suspicious: >1 email change) ---

def test_record_user_details_third_email_returns_suspicious():
    with patch("backend.tools.push"):
        record_user_details(email="a@b.com")
        record_user_details(email="b@b.com")   # correction
        result = record_user_details(email="c@b.com")  # suspicious
    assert result == {"recorded": "suspicious"}


def test_record_user_details_suspicious_no_push():
    with patch("backend.tools.push") as mock_push:
        record_user_details(email="a@b.com")
        record_user_details(email="b@b.com")
        record_user_details(email="c@b.com")
    assert mock_push.call_count == 1  # only the first


# --- rule 5 (override) ---

def test_record_user_details_override_allows_second_notification():
    with patch("backend.tools.push") as mock_push:
        record_user_details(email="a@b.com")
        result = record_user_details(email="new@b.com", override=True)
    assert result == {"recorded": "ok"}
    assert mock_push.call_count == 2


def test_record_user_details_override_used_twice_blocked():
    with patch("backend.tools.push"):
        record_user_details(email="a@b.com")
        record_user_details(email="new@b.com", override=True)
        result = record_user_details(email="third@b.com", override=True)
    assert result == {"recorded": "already_overridden"}


def test_record_user_details_override_on_fresh_session_still_records():
    with patch("backend.tools.push") as mock_push:
        result = record_user_details(email="a@b.com", override=True)
    assert result == {"recorded": "ok"}
    assert mock_push.call_count == 1


# --- session isolation ---

def test_different_sessions_are_independent():
    with patch("backend.tools.push") as mock_push:
        set_session_id("session-A")
        record_user_details(email="a@b.com")

        set_session_id("session-B")
        result = record_user_details(email="a@b.com")

    assert result == {"recorded": "ok"}
    assert mock_push.call_count == 2


# --- record_unknown_question ---

def test_record_unknown_question_returns_ok():
    with patch("backend.tools.push"):
        result = record_unknown_question(question="What is 42?")
    assert result["recorded"] == "ok"


def test_record_unknown_question_calls_push_with_question():
    with patch("backend.tools.push") as mock_push:
        record_unknown_question(question="What is 42?")
    mock_push.assert_called_once()
    assert "What is 42?" in mock_push.call_args[0][0]


# --- tools list ---

def test_tools_list_has_three_entries():
    assert len(tools) == 3


def test_tools_list_function_types():
    for tool in tools:
        assert tool["type"] == "function"
        assert "function" in tool


def test_tools_contain_expected_names():
    names = [t["function"]["name"] for t in tools]
    assert "record_user_details" in names
    assert "record_unknown_question" in names
    assert "check_question_similarity" in names
