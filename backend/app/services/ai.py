"""Optional AI narrative. Failure here must never affect scoring or the test record."""
import json
import logging

from ..core.config import settings

log = logging.getLogger("ai")

PROMPT_VERSION = "performance_analysis_v1"

SYSTEM = (
    "You are a supportive placement-preparation coach. You receive aggregate statistics from one practice test. "
    "Write a 2-3 sentence plain-language summary of the pattern you see and one concrete next step. "
    "Do not restate exact numbers already shown to the student, do not invent data, and never change or dispute the score."
)


def generate_narrative(stats: dict) -> str | None:
    """Return a short narrative or None (no key, timeout, malformed output, provider error)."""
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=settings.ai_timeout_seconds, max_retries=1)
        msg = client.messages.create(
            model=settings.ai_model, max_tokens=300, system=SYSTEM,
            messages=[{"role": "user", "content": json.dumps(stats)}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return text[:1200] or None
    except Exception as exc:  # noqa: BLE001 - deliberately broad: AI must degrade gracefully
        log.warning("AI narrative failed: %s", exc)
        return None
