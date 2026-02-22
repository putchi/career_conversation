from backend.models import Message, ChatRequest, ChatResponse


def test_message_stores_role_and_content():
    m = Message(role="user", content="hello")
    assert m.role == "user"
    assert m.content == "hello"


def test_message_assistant_role():
    m = Message(role="assistant", content="world")
    assert m.role == "assistant"


def test_chat_request_defaults_to_empty_history():
    req = ChatRequest(message="hi")
    assert req.message == "hi"
    assert req.history == []


def test_chat_request_accepts_history():
    history = [Message(role="user", content="prev")]
    req = ChatRequest(message="next", history=history)
    assert len(req.history) == 1
    assert req.history[0].role == "user"


def test_chat_response_stores_reply():
    r = ChatResponse(reply="hello back")
    assert r.reply == "hello back"
