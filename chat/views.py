import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from chat.services.chat_service import get_reply


@ensure_csrf_cookie
def county_select(request):
    """Render the county selection page."""
    return render(request, 'chat/county_select.html')


@ensure_csrf_cookie
def chat_view(request):
    """Render the main chat interface."""
    return render(request, 'chat/index.html')


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
