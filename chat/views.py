import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from chat.services.article_search import search_articles
from chat.services.chat_service import get_reply


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
    """Render the main chat interface."""
    return render(request, 'chat/index.html')


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
    """Handle chat API requests: accepts JSON { message, county }, returns OpenAI reply."""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        county = data.get('county', '')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    result = get_reply(message, county)

    if 'error' in result:
        return JsonResponse({'error': result['error']}, status=503)
    return JsonResponse({'reply': result['reply']})
