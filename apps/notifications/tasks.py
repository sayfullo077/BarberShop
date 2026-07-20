"""
Background tasks for sending appointment notifications and reminders.
django-q2 ishlatiladi: async_task() va Schedule orqali chaqiriladi.
"""
from datetime import timedelta
import logging

from django.utils import timezone

from apps.bookings.models import Appointment
from .senders import notify_user

logger = logging.getLogger(__name__)


def send_booking_confirmation(appointment_id: str):
    """Send booking confirmation to client and barber."""
    try:
        appt = Appointment.objects.select_related(
            "client", "barber__user", "service", "shop"
        ).get(id=appointment_id)
    except Appointment.DoesNotExist:
        return

    client_msg = (
        f"✅ <b>Bron tasdiqlandi!</b>\n\n"
        f"📅 Sana: <b>{appt.date.strftime('%d.%m.%Y')}</b>\n"
        f"⏰ Vaqt: <b>{appt.start_time.strftime('%H:%M')}</b>\n"
        f"✂️ Xizmat: <b>{appt.service.name}</b>\n"
        f"💈 Sartarosh: <b>{appt.barber.user.get_full_name()}</b>\n"
        f"📍 Salon: <b>{appt.shop.name}</b>\n\n"
        f"Bronni bekor qilish: /bekor_{appt.id}"
    )
    notify_user(appt.client, client_msg, appt, "booking_confirmed")

    barber_msg = (
        f"🆕 <b>Yangi bron!</b>\n\n"
        f"👤 Mijoz: <b>{appt.client.get_full_name() or appt.client.username}</b>\n"
        f"📅 Sana: <b>{appt.date.strftime('%d.%m.%Y')}</b>\n"
        f"⏰ Vaqt: <b>{appt.start_time.strftime('%H:%M')}</b>\n"
        f"✂️ Xizmat: <b>{appt.service.name}</b>"
    )
    notify_user(appt.barber.user, barber_msg, appt, "booking_confirmed")


def send_upcoming_reminders():
    """Send 1-hour reminders. Schedule: har 5 daqiqada."""
    now = timezone.localtime()
    reminder_time = now + timedelta(hours=1)

    appointments = Appointment.objects.filter(
        status__in=Appointment.ACTIVE_STATUSES,
        date=reminder_time.date(),
        start_time__gte=reminder_time.time(),
        start_time__lt=(reminder_time + timedelta(minutes=5)).time(),
        reminded_1h=False,
    ).select_related("client", "barber__user", "service", "shop")

    for appt in appointments:
        msg = (
            f"⏰ <b>Eslatma!</b> 1 soatdan so'ng bron.\n\n"
            f"📅 {appt.date.strftime('%d.%m.%Y')} soat <b>{appt.start_time.strftime('%H:%M')}</b>\n"
            f"✂️ {appt.service.name} — {appt.shop.name}"
        )
        notify_user(appt.client, msg, appt, "reminder_1h")
        appt.reminded_1h = True
        appt.save(update_fields=["reminded_1h"])


def send_5min_reminders():
    """
    Navbati yaqinlashgan mijozlarga 5 daqiqa oldin eslatma yuboradi.
    Schedule: har 1 daqiqada (aniqlik uchun).
    """
    now = timezone.localtime()
    window_end = now + timedelta(minutes=6)

    # Faqat bir kunlik oyna (yarim tunda o'tib ketmasligi uchun sana bo'yicha)
    appointments = Appointment.objects.filter(
        status__in=Appointment.ACTIVE_STATUSES,
        date=now.date(),
        start_time__gt=now.time(),
        start_time__lte=window_end.time(),
        reminded_5m=False,
    ).select_related("client", "barber__user", "service", "shop")

    for appt in appointments:
        msg = (
            f"🔔 <b>Navbatingiz yaqinlashdi!</b>\n\n"
            f"5 daqiqadan so'ng — soat <b>{appt.start_time.strftime('%H:%M')}</b>\n"
            f"✂️ {appt.service.name}\n"
            f"💈 {appt.barber.user.get_full_name() or appt.barber.user.username} — {appt.shop.name}\n\n"
            f"Iltimos, kechikmang. 🙏"
        )
        notify_user(appt.client, msg, appt, "reminder_5m")
        appt.reminded_5m = True
        appt.save(update_fields=["reminded_5m"])


def expire_appointments():
    """
    Vaqti o'tgan faol (pending/confirmed) bronlarni "Bajarildi" (COMPLETED)
    holatiga o'tkazadi — mijoz keyin baho bera oladi va usta faolligi ortadi.
    Schedule: har 5 daqiqada.
    """
    now = timezone.localtime()

    # Bugungi, vaqti allaqachon tugagan bronlar + o'tgan kunlardagi faol bronlar
    past_today = Appointment.objects.filter(
        status__in=Appointment.ACTIVE_STATUSES,
        date=now.date(),
        end_time__lt=now.time(),
    )
    past_days = Appointment.objects.filter(
        status__in=Appointment.ACTIVE_STATUSES,
        date__lt=now.date(),
    )
    count = 0
    for qs in (past_today, past_days):
        count += qs.update(
            status=Appointment.Status.COMPLETED,
            updated_at=now,
        )
    if count:
        logger.info("expire_appointments: %d ta bron bajarildi (completed).", count)
    return count


def send_day_before_reminders():
    """Send 24-hour reminders. Schedule: har soatda."""
    from datetime import timedelta as td
    tomorrow = (timezone.localtime() + td(days=1)).date()

    appointments = Appointment.objects.filter(
        status__in=Appointment.ACTIVE_STATUSES,
        date=tomorrow,
        reminded_24h=False,
    ).select_related("client", "barber__user", "service", "shop")

    for appt in appointments:
        msg = (
            f"📅 <b>Ertaga bron!</b>\n\n"
            f"Sana: <b>{appt.date.strftime('%d.%m.%Y')}</b>\n"
            f"Vaqt: <b>{appt.start_time.strftime('%H:%M')}</b>\n"
            f"✂️ {appt.service.name} — {appt.shop.name}"
        )
        notify_user(appt.client, msg, appt, "reminder_24h")
        appt.reminded_24h = True
        appt.save(update_fields=["reminded_24h"])


# ── Re-engagement (retention): qaytmagan mijozlarni qaytarish ──────────────
REENGAGE_AFTER_DAYS = 30      # soch olish sikli ~ 3-4 hafta
REENGAGE_COOLDOWN_DAYS = 30   # bir mijozga ko'pi bilan shuncha kunda 1 marta


def send_reengagement_nudges():
    """«Vaqt keldi 💈» — oxirgi tashrifi REENGAGE_AFTER_DAYS kundan oshgan va
    kelgusi faol broni yo'q mijozlarga qaytishga yumshoq eslatma. Anti-spam:
    last_reengaged_at cooldown. Schedule: kuniga bir marta (kunduzi)."""
    from django.db.models import Max
    from apps.accounts.models import User

    today = timezone.localdate()
    now = timezone.now()
    visit_cutoff = today - timedelta(days=REENGAGE_AFTER_DAYS)
    cooldown_cutoff = now - timedelta(days=REENGAGE_COOLDOWN_DAYS)

    candidates = (
        User.objects.filter(
            appointments__status=Appointment.Status.COMPLETED,
            is_blocked=False,
            telegram_id__isnull=False,
        )
        .annotate(last_visit=Max("appointments__date"))
        .filter(last_visit__lte=visit_cutoff)
        .distinct()
    )

    sent = 0
    for u in candidates:
        # Anti-spam: yaqinda eslatilgan bo'lsa — o'tkazib yuboramiz
        if u.last_reengaged_at and u.last_reengaged_at >= cooldown_cutoff:
            continue
        # Kelgusi faol broni bo'lsa — eslatma shart emas
        if u.appointments.filter(
            status__in=Appointment.ACTIVE_STATUSES, date__gte=today
        ).exists():
            continue
        last_appt = (
            u.appointments.select_related("shop")
            .order_by("-date", "-start_time")
            .first()
        )
        shop_name = last_appt.shop.name if last_appt and last_appt.shop_id else None
        msg = (
            f"💈 <b>Vaqt keldi!</b>\n\n"
            f"Oxirgi tashrifingizdan beri bir oz vaqt o'tdi. "
            f"Yangi navbatga yozilishni xohlaysizmi?"
            + (f"\n\n📍 <b>{shop_name}</b> sizni kutadi." if shop_name else "")
            + "\n\nIlovani ochib qulay vaqtni tanlang. ✂️"
        )
        notify_user(u, msg, None, "reengagement")
        u.last_reengaged_at = now
        u.save(update_fields=["last_reengaged_at"])
        sent += 1

    if sent:
        logger.info("send_reengagement_nudges: %d ta mijozga eslatma yuborildi.", sent)
    return sent


def send_cancellation_notice(appointment_id: str):
    """Notify barber when client cancels."""
    try:
        appt = Appointment.objects.select_related(
            "client", "barber__user", "service"
        ).get(id=appointment_id)
    except Appointment.DoesNotExist:
        return

    msg = (
        f"❌ <b>Bron bekor qilindi</b>\n\n"
        f"👤 Mijoz: {appt.client.get_full_name() or appt.client.username}\n"
        f"📅 {appt.date.strftime('%d.%m.%Y')} soat {appt.start_time.strftime('%H:%M')}\n"
        f"✂️ {appt.service.name}"
    )
    notify_user(appt.barber.user, msg, appt, "cancelled")


def notify_join_request(request_id: str):
    """Salon egasiga yangi qo'shilish so'rovi haqida xabar."""
    from apps.shops.models import ShopJoinRequest
    try:
        jr = ShopJoinRequest.objects.select_related("barber", "shop__owner").get(id=request_id)
    except ShopJoinRequest.DoesNotExist:
        return
    barber_name = jr.barber.get_full_name() or jr.barber.username
    msg = (
        f"🙋 <b>Yangi qo'shilish so'rovi!</b>\n\n"
        f"💈 Sartarosh: <b>{barber_name}</b>\n"
        f"🏠 Salon: <b>{jr.shop.name}</b>\n"
        + (f"📞 {jr.barber.phone}\n" if jr.barber.phone else "")
        + (f"\n💬 {jr.message}" if jr.message else "")
        + "\n\nIlovadagi «Salon boshqaruvi» bo'limidan javob bering."
    )
    notify_user(jr.shop.owner, msg, None, "join_request")


def notify_join_response(request_id: str):
    """Barberga so'rov javobi (qabul/rad) haqida xabar."""
    from apps.shops.models import ShopJoinRequest
    try:
        jr = ShopJoinRequest.objects.select_related("barber", "shop").get(id=request_id)
    except ShopJoinRequest.DoesNotExist:
        return
    if jr.status == ShopJoinRequest.Status.APPROVED:
        msg = (
            f"✅ <b>Qabul qilindingiz!</b>\n\n"
            f"«{jr.shop.name}» saloniga a'zo bo'ldingiz. "
            f"Endi shu salon ostida bron qabul qilasiz."
        )
    else:
        msg = (
            f"🚫 <b>So'rov rad etildi</b>\n\n"
            f"«{jr.shop.name}» saloniga qo'shilish so'rovingiz qabul qilinmadi. "
            f"Siz mustaqil faoliyatingizni davom ettirasiz."
        )
    notify_user(jr.barber, msg, None, "join_response")
