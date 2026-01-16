from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
import json


@ensure_csrf_cookie
def index(request):
    """Render the main chat interface."""
    return render(request, 'chat/index.html')


@require_http_methods(["POST"])
def chat_api(request):
    """Handle chat API requests."""
    try:
        data = json.loads(request.body)
        message = data.get('message', '')
        
        # Mock response
        return JsonResponse({'reply': 'This is a mock response.'})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
