"""Chat page: form, validation, CSRF, and no stored history."""

from app.models import Expense
from app.services.chatbot_service import MAX_QUESTION_LENGTH


def test_chat_page_shows_the_form(client):
    response = client.get("/chat")
    assert response.status_code == 200
    assert b'name="question"' in response.data
    assert b"Questions are not saved." in response.data


def test_asking_returns_an_answer(client):
    response = client.post("/chat", data={"question": "What is inflation?"})
    assert response.status_code == 200
    assert b"Answer" in response.data
    assert b"/learn/inflation" in response.data


def test_empty_question_is_400_with_message(client):
    response = client.post("/chat", data={"question": "  "})
    assert response.status_code == 400
    assert b"Type a question" in response.data


def test_too_long_question_is_400(client):
    response = client.post("/chat", data={"question": "x" * (MAX_QUESTION_LENGTH + 1)})
    assert response.status_code == 400
    assert b"Please keep questions under" in response.data


def test_chat_page_is_public(client):
    assert client.get("/chat").status_code == 200


def test_questions_are_not_stored(app, client):
    client.post("/chat", data={"question": "What is inflation?"})
    assert Expense.query.count() == 0
    # The chat has no table of its own; nothing is persisted.
    assert "chat" not in {t for t in app.extensions["sqlalchemy"].metadata.tables}


def test_csrf_protects_the_question_form_when_enabled(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post("/chat", data={"question": "What is inflation?"})
    assert response.status_code == 400
    assert b"CSRF" in response.data


def test_question_is_echoed_safely(client):
    response = client.post("/chat", data={"question": "<script>alert(1)</script> inflation"})
    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;" in response.data
