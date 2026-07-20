from django.urls import path
from . import views, api_views

app_name = "telegram"

urlpatterns = [
    path("", views.webapp_index, name="webapp"),
    path("webhook/", views.webhook, name="webhook"),

    # Client API
    path("api/me/", api_views.me, name="api_me"),
    path("api/audience-pref/", api_views.set_audience_pref, name="api_audience_pref"),
    path("api/verify-phone/", api_views.verify_phone, name="api_verify_phone"),
    path("api/shops/", api_views.shops_list, name="api_shops"),
    path("api/search/", api_views.search, name="api_search"),
    path("api/nearby/", api_views.nearby, name="api_nearby"),
    path("api/shops/<slug:slug>/", api_views.shop_detail, name="api_shop_detail"),
    path("api/slots/", api_views.slots_api, name="api_slots"),
    path("api/bookings/", api_views.booking_create, name="api_booking_create"),
    path("api/my-bookings/", api_views.my_bookings, name="api_my_bookings"),
    path("api/bookings/<uuid:appointment_id>/cancel/", api_views.booking_cancel, name="api_booking_cancel"),
    path("api/reviews/", api_views.review_create, name="api_review_create"),
    path("api/reports/", api_views.report_create, name="api_report_create"),

    # Barber API
    path("api/barber/register/", api_views.barber_register, name="api_barber_register"),
    path("api/barber/predefined-services/", api_views.predefined_services, name="api_predefined_services"),
    path("api/barber/services/", api_views.barber_services, name="api_barber_services"),
    path("api/barber/services/<uuid:service_id>/", api_views.barber_service_delete, name="api_barber_service_delete"),
    path("api/barber/dashboard/", api_views.barber_dashboard, name="api_barber_dashboard"),
    path("api/barber/toggle-accepting/", api_views.barber_toggle_accepting, name="api_barber_toggle_accepting"),
    path("api/barber/profile/update/", api_views.update_barber_profile, name="api_barber_profile_update"),
    path("api/barber/shop/logo/", api_views.upload_shop_logo, name="api_shop_logo"),

    # Salon management (owner)
    path("api/shop/update/", api_views.shop_update, name="api_shop_update"),
    path("api/shop/cover/", api_views.upload_shop_cover, name="api_shop_cover"),
    path("api/shop/delete/", api_views.shop_delete, name="api_shop_delete"),

    # Join requests
    path("api/join-requests/", api_views.join_requests_list, name="api_join_requests"),
    path("api/join-requests/create/", api_views.join_request_create, name="api_join_request_create"),
    path("api/join-requests/mine/", api_views.my_join_requests, name="api_join_requests_mine"),
    path("api/join-requests/<uuid:request_id>/respond/", api_views.join_request_respond, name="api_join_request_respond"),

    # Upload & Support
    path("api/upload/", api_views.upload_image, name="api_upload"),
    path("api/me/avatar/", api_views.upload_avatar, name="api_upload_avatar"),
    path("api/support/", api_views.support_message, name="api_support"),
]
