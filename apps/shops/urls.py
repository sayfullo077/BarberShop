from django.urls import path
from . import views

app_name = "shops"

urlpatterns = [
    path("", views.home, name="home"),
    path("salonlar/", views.ShopListView.as_view(), name="list"),
    path("salon/<slug:slug>/", views.ShopDetailView.as_view(), name="detail"),
    path("sartarosh/<uuid:pk>/", views.BarberDetailView.as_view(), name="barber_detail"),
]
