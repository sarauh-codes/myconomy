"""Economic chat page. Nothing is stored: each question is answered and then forgotten."""

from flask import Blueprint, render_template, request

from ..services.chatbot_service import MAX_QUESTION_LENGTH, answer

chat_bp = Blueprint("chat", __name__)


@chat_bp.get("/chat")
def chat():
    return render_template("chat.html", result=None, question="", max_length=MAX_QUESTION_LENGTH)


@chat_bp.post("/chat")
def ask():
    question = request.form.get("question", "")
    result = answer(question)
    status = 400 if result.kind in ("too_long", "empty") else 200
    return render_template(
        "chat.html",
        result=result,
        question=question[:MAX_QUESTION_LENGTH],
        max_length=MAX_QUESTION_LENGTH,
    ), status
