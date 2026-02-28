import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from chat.services.article_search import search_articles
from chat.services.chat_service import get_reply
from chat.services.hardiness import get_hardiness_for_zip
from chat.categories import MAIN_CATEGORIES, SUBCATEGORY_MAP


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


@ensure_csrf_cookie
def hardiness_view(request):
    """Render the hardiness zone lookup page (enter ZIP to get zone)."""
    county = request.GET.get("county", "").strip()
    return render(request, "chat/hardiness.html", {"county": county})


def hardiness_api(request):
    """GET ?zip=... returns JSON { zone: '...' } or { error: '...' }."""
    zip_code = (request.GET.get("zip") or "").strip()
    if not zip_code:
        return JsonResponse({"error": "Please enter a ZIP code."}, status=400)
    csv_path = getattr(settings, "HARDINESS_ZONE_CSV_PATH", None)
    zone = get_hardiness_for_zip(zip_code, csv_path)
    if zone is None:
        return JsonResponse({"error": "No hardiness zone found for that ZIP code."}, status=404)
    return JsonResponse({"zone": zone})


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
    """Handle chat API: JSON { message, county, category?, subcategory?, chat_history? }."""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        county = data.get('county', '')
        category = data.get('category', '')
        subcategory = data.get('subcategory', '')
        chat_history = data.get('chat_history')
        if not isinstance(chat_history, list):
            chat_history = None
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    result = get_reply(
        message,
        county,
        category=category,
        subcategory=subcategory,
        chat_history=chat_history,
    )

    if 'error' in result:
        return JsonResponse({'error': result['error']}, status=503)
    return JsonResponse({'reply': result['reply']})
