"""
Chat service: retrieval from fact sheets + OpenAI with county-constrained assistant.
Uses Backend fact_sheets.db and County Contact CSV when available.
When AG_EXTENSION_API_URL is set, calls that API first (12k-article assistant).
"""

import json
import logging
import re
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from django.conf import settings

logger = logging.getLogger(__name__)
from openai import OpenAI

from chat.services.article_search import resolve_uploaded_link
from chat.services.retrieval import get_county_contacts, retrieve_relevant_papers

FALLBACK_REPLY = "Sorry, I'm unable to generate a response right now. Please try again later."
API_KEY_MISSING_MESSAGE = "Sorry, I'm unable to generate a response right now. Please try again later."

# Max number of prior exchanges to send as context (each exchange = user + assistant)
MAX_CHAT_HISTORY_EXCHANGES = 10


def _call_ag_extension_api(message: str) -> str | None:
    """POST /ask to AG Extension API. Returns response text or None on failure."""
    base = getattr(settings, "AG_EXTENSION_API_URL", "") or ""
    if not base:
        return None
    url = base.rstrip("/") + "/ask"
    try:
        req = Request(
            url,
            data=json.dumps({"message": message}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=65) as resp:
            data = json.loads(resp.read().decode())
            return (data.get("response") or "").strip() or None
    except HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            detail = json.loads(body).get("detail", body)
        except Exception:
            detail = body or str(e)
        logger.warning("AG Extension API error %s: %s", e.code, detail)
        return None
    except (URLError, json.JSONDecodeError, OSError) as e:
        logger.warning("AG Extension API call failed: %s", e)
        return None


def get_reply(
    message: str,
    county: str,
    *,
    category: str = "",
    subcategory: str = "",
    chat_history: list | None = None,
) -> dict:
    """
    Get a reply: retrieve fact sheets, then OpenAI with context or county-contact fallback.
    When AG_EXTENSION_API_URL is set, calls that API first (single message; no history).
    Optional: category/subcategory (included in prompt), chat_history (local path only).
    Returns {"reply": "<text>"} on success, {"error": "<message>"} on missing API key.
    """
    county_display = (county or "Utah").strip() or "Utah"
    message_clean = (message or "").strip() or "Hello"

    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""

    api_url = getattr(settings, "AG_EXTENSION_API_URL", "") or ""
    if api_url:
        api_message = f"The user is in {county_display} County, Utah. Question: {message_clean}"
        reply = _call_ag_extension_api(api_message)
        if reply:
            logger.info("Chat reply from AG Extension API")
            reply = re.sub(
                r"\]\(uploaded://(.+?\.pdf)\)",
                lambda m: "](uploaded://" + m.group(1).replace(" ", "%20") + ")",
                reply,
            )
            return {"reply": reply or FALLBACK_REPLY}
        logger.info("AG Extension API returned no reply, using local path")

    if not api_key:
        return {"error": API_KEY_MISSING_MESSAGE}

    db_path = getattr(settings, "FACT_SHEETS_DB_PATH", None)
    csv_path = getattr(settings, "COUNTY_CONTACTS_CSV_PATH", None)
    articles_db_path = getattr(settings, "EXTENSION_ARTICLES_DB_PATH", None)

    papers = retrieve_relevant_papers(message_clean, db_path)

    if papers:
        context = ""
        for idx, p in enumerate(papers, 1):
            link = p["link"]
            if articles_db_path:
                link = resolve_uploaded_link(link, articles_db_path)
            context += f"\nDocument {idx}: {p['title']}\n"
            context += f"Subject: {p['subject']}\n"
            context += f"Content excerpt: {p['content']}\n"
            context += f"Link: {link}\n"

        category_line = ""
        if subcategory and subcategory.strip():
            category_line = f" The user is asking about: {subcategory.strip()}."
        elif category and category.strip():
            category_line = f" The user is asking about: {category.strip()}."

        system_content = f"""You are Agnes, a friendly and professional agricultural extension assistant for Utah State University Extension.
You help people in {county_display} County, Utah.{category_line}

PERSONA AND TONE:
- You are \"Agnes\", the USU Extension office assistant.
- Use a warm, encouraging, and professional tone.
- When it is natural (especially for a user's first question), you may start with a short greeting like: \"Hi! I'm Agnes, your Extension office assistant...\"
- Write in the first person as Agnes (\"I\"), and focus on being clear and supportive.

INSTRUCTIONS:
1. Provide a brief summary (2-3 sentences) of what might be causing the issue or answering their question.
2. Then cite the relevant fact sheets with their titles and links.
3. End by asking if they need more help with this topic or anything related.

Keep responses concise and helpful.

Format all responses using clean Markdown.
Use:
- Paragraph spacing
- Bullet points when appropriate
- Bold section headers when helpful
- Proper Markdown links: [Title](URL)

Do not return raw HTML."""

        user_content = f"Question: {message_clean}\n\nAvailable resources:{context}"

        # Build messages: system, optional chat history, current user message
        messages = [{"role": "system", "content": system_content}]
        if chat_history and isinstance(chat_history, list):
            n = MAX_CHAT_HISTORY_EXCHANGES * 2  # cap total messages
            for m in chat_history[-n:]:
                if isinstance(m, dict) and m.get("role") and m.get("content") is not None:
                    messages.append({"role": m["role"], "content": str(m["content"])})
        messages.append({"role": "user", "content": user_content})

        logger.info("Chat reply from local retrieval + OpenAI")
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=600,
            )
            reply = (
                (response.choices[0].message.content or "").strip()
                if response.choices
                else ""
            )
            # Fix uploaded:// links with spaces so Markdown renders one clickable link
            reply = re.sub(
                r"\]\(uploaded://(.+?\.pdf)\)",
                lambda m: "](uploaded://" + m.group(1).replace(" ", "%20") + ")",
                reply,
            )
            return {"reply": reply or FALLBACK_REPLY}
        except Exception:
            return {"reply": FALLBACK_REPLY}

    logger.info("Chat reply from local fallback (no matching fact sheets)")
    contacts = get_county_contacts(county_display, csv_path)
    if contacts:
        contact_lines = []
        for c in contacts:
            contact_lines.append(f"{c['name']}\n{c['title']}\n{c['email']}\n{c['phone']}")
        contact_block = "\n\n".join(contact_lines)
        fallback = (
            f"I couldn't find fact sheets in our database that directly answer your question about \"{message_clean}\".\n\n"
            f"For help specific to {county_display} County, I recommend reaching out to your local Extension office:\n\n{contact_block}\n\n"
            "They can provide county-specific guidance and connect you with additional resources."
        )
    else:
        fallback = (
            f"I couldn't find relevant fact sheets for your question.\n\n"
            "Please try rephrasing your question or contacting your local USU Extension office for personalized assistance."
        )
    return {"reply": fallback}
