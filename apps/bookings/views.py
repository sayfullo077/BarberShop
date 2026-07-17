import json
from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_GET, require_POST

from apps.shops.models import BarberProfile, Shop
from apps.services.models import Service
from .models import Appointment
from .services import get_available_slots, create_appointment


@login_required
def booking_page(request, shop_slug):
    shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
    barbers = shop.barbers.filter(is_accepting_bookings=True).select_related("user")
    services = shop.services.filter(is_active=True).select_related("category")
    return render(request, "pages/booking.html", {
        "shop": shop,
        "barbers": barbers,
        "services": services,
    })


@require_GET
def available_slots_api(request):
    """AJAX: returns available time slots for a barber on a given date."""
    barber_id = request.GET.get("barber_id")
    date_str = request.GET.get("date")

    if not barber_id or not date_str:
        return JsonResponse({"error": "barber_id va date kerak"}, status=400)

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"error": "Noto'g'ri sana formati"}, status=400)

    if selected_date < date.today():
        return JsonResponse({"slots": []})

    barber = get_object_or_404(BarberProfile, id=barber_id, is_accepting_bookings=True)
    slots = get_available_slots(barber, selected_date)

    return JsonResponse({
        "slots": [s.strftime("%H:%M") for s in slots],
        "slot_duration": barber.slot_duration,
    })


@login_required
@require_POST
def create_booking(request):
    """AJAX/form: creates a new appointment."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        data = request.POST.dict()

    barber = get_object_or_404(BarberProfile, id=data.get("barber_id"), is_accepting_bookings=True)
    service = get_object_or_404(Service, id=data.get("service_id"), is_active=True, shop=barber.shop)

    try:
        selected_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
        start_time = datetime.strptime(data["time"], "%H:%M").time()
    except (KeyError, ValueError):
        return JsonResponse({"error": "Sana yoki vaqt noto'g'ri"}, status=400)

    try:
        appointment = create_appointment(
            client=request.user,
            barber=barber,
            service=service,
            date=selected_date,
            start_time=start_time,
        )
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=409)

    from django_q.tasks import async_task
    async_task("apps.notifications.tasks.send_booking_confirmation", str(appointment.id))

    return JsonResponse({
        "ok": True,
        "appointment_id": str(appointment.id),
        "redirect": f"/bronlar/{appointment.id}/",
    })


@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related("barber__user", "service", "shop", "client"),
        id=pk,
        client=request.user,
    )
    return render(request, "pages/appointment_detail.html", {"appointment": appointment})


@login_required
def my_appointments(request):
    appointments = (
        Appointment.objects.filter(client=request.user)
        .select_related("barber__user", "service", "shop")
        .order_by("-date", "-start_time")
    )
    return render(request, "pages/my_appointments.html", {"appointments": appointments})


@login_required
@require_POST
def cancel_appointment(request, pk):
    appointment = get_object_or_404(Appointment, id=pk, client=request.user)
    if appointment.status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
        return JsonResponse({"error": "Bu bronni bekor qilib bo'lmaydi"}, status=400)

    appointment.cancel()
    from django_q.tasks import async_task
    async_task("apps.notifications.tasks.send_cancellation_notice", str(appointment.id))

    return JsonResponse({"ok": True})
