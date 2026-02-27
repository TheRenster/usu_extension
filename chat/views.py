import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from chat.services.article_search import search_articles
from chat.services.chat_service import get_reply
from chat.categories import MAIN_CATEGORIES, SUBCATEGORY_MAP
from .models import Conversation, Message, Feedback


@ensure_csrf_cookie
def county_select(request):
    """Render the county selection page."""
    return render(request, 'chat/county_select.html')


@ensure_csrf_cookie
def hub_view(request):
    """Choice: search for an article or ask a question."""
    county = request.GET.get("county", "").strip()
    return render(request, "chat/hub.html", {"county": county})


@ensure_csrf_cookie
def chat_view(request):
    """Render the main chat interface with category options."""
    return render(request, 'chat/index.html', {
        'main_categories': MAIN_CATEGORIES,
        'subcategory_map': SUBCATEGORY_MAP,
    })


@ensure_csrf_cookie
def search_view(request):
    """Render the article search page."""
    county = request.GET.get("county", "").strip()
    return render(request, "chat/search.html", {"county": county})


def search_api(request):
    """GET ?q=... returns JSON { results: [{ url, title }, ...] }."""
    q = (request.GET.get("q") or "").strip()
    db_path = getattr(settings, "EXTENSION_ARTICLES_DB_PATH", None)
    if not db_path or not db_path.exists():
        return JsonResponse({"results": []})
    results = search_articles(q, db_path)
    return JsonResponse({"results": results})


@require_http_methods(["POST"])
def chat_api(request):
    """
    Handle chat API.

    Accepts JSON:
    {
        "message": "<user text>",
        "county": "<county name>",
        "category": "<optional category>",
        "subcategory": "<optional subcategory>",
        "chat_history": [...],
        "image_base64": "<optional base64 image>",
        "conversation_id": "<optional UUID>"
    }

    Returns JSON:
    {
        "reply": "<assistant text>",
        "conversation_id": "<UUID for this conversation>"
    }
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        county = data.get('county', '')
        category = data.get('category', '')
        subcategory = data.get('subcategory', '')
        chat_history = data.get('chat_history')
        if not isinstance(chat_history, list):
            chat_history = None
        image_base64 = data.get('image_base64') or ''
        conversation_id = data.get('conversation_id')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    conversation = None
    if conversation_id:
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            conversation = None

    if conversation is None:
        conversation = Conversation.objects.create(county=county or "")

    # Store the incoming user message
    if message:
        Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_USER,
            content=message,
        )

    result = get_reply(
        message,
        county,
        category=category,
        subcategory=subcategory,
        chat_history=chat_history,
        image_base64=image_base64 or None,
    )

    if 'error' in result:
        return JsonResponse({'error': result['error']}, status=503)

    reply_text = result.get('reply', '')
    if reply_text:
        Message.objects.create(
            conversation=conversation,
            role=Message.ROLE_ASSISTANT,
            content=reply_text,
        )

    return JsonResponse({'reply': reply_text, 'conversation_id': str(conversation.id)})


@require_http_methods(["POST"])
def feedback_api(request):
    """
    Accept feedback for a conversation.

    Expected JSON:
    {
        "conversation_id": "<UUID>",
        "rating": "up" or "down",
        "comment": "<optional free text>"
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    conversation_id = data.get('conversation_id')
    rating = data.get('rating')
    comment = (data.get('comment') or '').strip()

    if not conversation_id:
        return JsonResponse({'error': 'conversation_id is required'}, status=400)

    if rating not in (Feedback.RATING_UP, Feedback.RATING_DOWN):
        return JsonResponse({'error': 'Invalid rating'}, status=400)

    try:
        conversation = Conversation.objects.get(id=conversation_id)
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)

    Feedback.objects.create(
        conversation=conversation,
        rating=rating,
        comment=comment,
    )

    return JsonResponse({'status': 'ok'})
