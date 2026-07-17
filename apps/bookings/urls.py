from django.urls import path
from . import views

app_name = "bookings"

urlpatterns = [
    path("bron/<slug:shop_slug>/", views.booking_page, name="book"),
    path("api/slots/", views.available_slots_api, name="slots_api"),
    path("api/create/", views.create_booking, name="create"),
    path("<uuid:pk>/", views.appointment_detail, name="detail"),
    path("mening-bronlarim/", views.my_appointments, name="my_list"),
    path("<uuid:pk>/bekor/", views.cancel_appointment, name="cancel"),
]
