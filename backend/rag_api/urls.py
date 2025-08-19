from django.urls import path
from . import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("query", views.query, name="query"),
    path("token", views.obtain_token, name="token"),
]
