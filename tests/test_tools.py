from unittest.mock import patch

from backend.tools import push, record_user_details, record_unknown_question, tools


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


def test_record_unknown_question_returns_ok():
    with patch("backend.tools.push"):
        result = record_unknown_question(question="What is 42?")
    assert result == {"recorded": "ok"}


def test_record_unknown_question_calls_push_with_question():
    with patch("backend.tools.push") as mock_push:
        record_unknown_question(question="What is 42?")
    mock_push.assert_called_once()
    assert "What is 42?" in mock_push.call_args[0][0]


def test_tools_list_has_two_entries():
    assert len(tools) == 2


def test_tools_list_function_types():
    for tool in tools:
        assert tool["type"] == "function"
        assert "function" in tool


def test_tools_contain_record_user_details():
    names = [t["function"]["name"] for t in tools]
    assert "record_user_details" in names


def test_tools_contain_record_unknown_question():
    names = [t["function"]["name"] for t in tools]
    assert "record_unknown_question" in names
