"""
Chat service: calls OpenAI with county-constrained horticulture assistant behavior.
No RAG, no memory, no database — controlled prompting only.
"""

from django.conf import settings
from openai import OpenAI


SYSTEM_PROMPT_TEMPLATE = """You are a Utah State University Extension horticulture assistant.
Only provide horticulture advice relevant to {county} County, Utah.
If a question is not related to horticulture or not relevant to {county} County, politely explain that you specialize in horticulture for that county only.
Keep answers practical, concise, and research-aligned."""

FALLBACK_REPLY = "Sorry, I'm unable to generate a response right now. Please try again later."
API_KEY_MISSING_MESSAGE = "OpenAI API key is not configured. Please set OPENAI_API_KEY in your .env file."


def get_reply(message: str, county: str) -> dict:
    """
    Get a reply from OpenAI constrained to the given Utah county.
    Returns {"reply": "<text>"} on success.
    Returns {"error": "<message>"} on missing API key or API failure (no server crash).
    """
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key:
        return {"error": API_KEY_MISSING_MESSAGE}

    county_display = (county or "Utah").strip() or "Utah"
    system_content = SYSTEM_PROMPT_TEMPLATE.format(county=county_display)

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": (message or "").strip() or "Hello"},
            ],
        )
        reply = (
            (response.choices[0].message.content or "").strip()
            if response.choices
            else ""
        )
        return {"reply": reply or FALLBACK_REPLY}
    except Exception:
        return {"reply": FALLBACK_REPLY}
