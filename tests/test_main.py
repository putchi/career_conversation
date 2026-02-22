import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.main import app


@pytest.fixture
def client_with_me():
    """TestClient with a mocked Me instance, lifespan triggered."""
    mock_me = MagicMock()
    mock_me.chat.return_value = "test reply"
    with patch.object(main_module, "Me", return_value=mock_me):
        with TestClient(app) as client:
            yield client, mock_me


def test_health_returns_ok(client_with_me):
    client, _ = client_with_me
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_endpoint_returns_reply(client_with_me):
    client, mock_me = client_with_me
    response = client.post("/api/chat", json={"message": "hello", "history": []})
    assert response.status_code == 200
    assert response.json() == {"reply": "test reply"}


def test_chat_endpoint_passes_message_to_me(client_with_me):
    client, mock_me = client_with_me
    client.post("/api/chat", json={"message": "hello world", "history": []})
    args = mock_me.chat.call_args[0]
    assert args[0] == "hello world"


def test_chat_endpoint_converts_history(client_with_me):
    client, mock_me = client_with_me
    client.post("/api/chat", json={
        "message": "next",
        "history": [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ],
    })
    _, history = mock_me.chat.call_args[0]
    assert history == [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
    ]


def test_config_js_content_type(client_with_me):
    client, _ = client_with_me
    response = client.get("/config.js")
    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


def test_config_js_sets_window_variable(client_with_me):
    client, _ = client_with_me
    response = client.get("/config.js")
    assert "window.CAREER_CONFIG" in response.text


def test_config_js_includes_env_values(client_with_me, monkeypatch):
    client, _ = client_with_me
    monkeypatch.setenv("VITE_OWNER_NAME", "Alex Rabinovich")
    monkeypatch.setenv("VITE_OWNER_TITLE", "Software Engineer")
    monkeypatch.setenv("VITE_LINKEDIN_URL", "https://linkedin.com/in/alex")
    response = client.get("/config.js")
    content = response.text
    # Parse the JSON embedded in the JS
    json_str = content[len("window.CAREER_CONFIG = "):-1]
    config = json.loads(json_str)
    assert config["ownerName"] == "Alex Rabinovich"
    assert config["ownerTitle"] == "Software Engineer"
    assert config["linkedinUrl"] == "https://linkedin.com/in/alex"


def test_config_js_defaults_to_empty_strings(client_with_me, monkeypatch):
    client, _ = client_with_me
    monkeypatch.delenv("VITE_OWNER_NAME", raising=False)
    monkeypatch.delenv("VITE_OWNER_TITLE", raising=False)
    monkeypatch.delenv("VITE_LINKEDIN_URL", raising=False)
    response = client.get("/config.js")
    json_str = response.text[len("window.CAREER_CONFIG = "):-1]
    config = json.loads(json_str)
    assert config == {"ownerName": "", "ownerTitle": "", "linkedinUrl": ""}
