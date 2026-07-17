from django.urls import path
from . import views

app_name = "portfolio"

urlpatterns = [
    path("api/<slug:shop_slug>/", views.portfolio_api, name="api"),
]
