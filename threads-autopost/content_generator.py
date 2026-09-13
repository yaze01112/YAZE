"""Generate Threads post text with Claude.

Requires ANTHROPIC_API_KEY (or another credential source the Anthropic SDK
picks up automatically, e.g. `ant auth login`).
"""
from __future__ import annotations

import anthropic

MAX_THREADS_CHARS = 500
DEFAULT_MODEL = "claude-opus-5"


def generate_post(topic: str, style: str = "", model: str = DEFAULT_MODEL) -> str:
    """Generate a single Threads post (<=500 chars) about the given topic."""
    client = anthropic.Anthropic()

    system = (
        "You write short, engaging posts for Threads (Meta's text-based social "
        "app). Hard limit: 500 characters. Plain text only, no markdown, no "
        "hashtag spam (at most 1-2 relevant hashtags if truly useful). Output "
        "only the post text itself, nothing else - no preamble, no quotes."
    )
    if style:
        system += f" Tone/style: {style}."

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": f"Write a Threads post about: {topic}"}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    return text[:MAX_THREADS_CHARS]
