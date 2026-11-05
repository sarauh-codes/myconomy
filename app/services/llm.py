"""Optional language-model provider, behind a small interface.

The chatbot answers from verified data without a language model, so this
module is only the seam for adding one later. No external provider is wired
up. The default provider sends nothing outside the application.

Before a real provider is added, the design requires:
- an exact model version, and a documented privacy review;
- that only retrieved facts are sent, never personal records (FR-06);
- timeouts, rate-limit handling, and a fallback to the non-AI answer (FR-06).
"""

from __future__ import annotations

from typing import Protocol


class ChatProvider(Protocol):
    name: str

    def phrase(self, question: str, facts: list[str]) -> str | None:
        """Return a model-written answer that uses only the given facts, or None to use the built-in answer."""
        ...


class NoExternalProvider:
    """Default. Never sends anything outside the application."""

    name = "none"

    def phrase(self, question: str, facts: list[str]) -> str | None:
        return None


def get_provider(name: str | None = None) -> ChatProvider:
    """Return the configured provider. Unknown names fall back to the built-in answers."""
    if not name or name == "none":
        return NoExternalProvider()
    # No external provider is implemented yet, so unknown names use the built-in answers.
    return NoExternalProvider()
