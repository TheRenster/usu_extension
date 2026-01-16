"""
URL configuration for chatbot_site project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('chat.urls')),
]
