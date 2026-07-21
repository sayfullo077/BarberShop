"""
Booking business logic — slot generation and availability checks.
Dynamic availability: slot generation depends on the required total duration,
so multi-service bookings only see time-slots that actually fit.
"""
from datetime import datetime, timedelta, time, date as date_type
from typing import List

from .models import Appointment, BlockedSlot
from apps.shops.models import BarberProfile, WorkingHours


def get_available_slots(barber: BarberProfile, date: date_type, duration: int = None) -> List[time]:
    """
    Berilgan barber, sana va kerakli DAVOMIYLIK uchun bo'sh boshlanish vaqtlari.
    Ish vaqti, mavjud bronlar (to'liq oralik overlap) va bloklarni hisobga oladi.
    `duration` — daqiqada (masalan tanlangan xizmatlar yig'indisi). Bo'sh bo'lsa
    barber.slot_duration ishlatiladi.
    """
    day_of_week = date.weekday()
    try:
        wh = WorkingHours.objects.get(shop=barber.shop, day_of_week=day_of_week)
    except WorkingHours.DoesNotExist:
        return []
    if wh.is_day_off:
        return []

    step = timedelta(minutes=barber.slot_duration or 30)
    need = timedelta(minutes=duration or barber.slot_duration or 30)

    # Mavjud band oraliklar: bronlar (start..end) + bloklar
    intervals = []
    for s, e in Appointment.objects.filter(
        barber=barber, date=date, status__in=Appointment.ACTIVE_STATUSES,
    ).values_list("start_time", "end_time"):
        intervals.append((datetime.combine(date, s), datetime.combine(date, e)))
    for s, e in BlockedSlot.objects.filter(barber=barber, date=date).values_list(
        "start_time", "end_time"
    ):
        intervals.append((datetime.combine(date, s), datetime.combine(date, e)))

    now = datetime.now()
    slots = []
    current = datetime.combine(date, wh.open_time)
    end_of_day = datetime.combine(date, wh.close_time)

    while current + need <= end_of_day:
        s_start, s_end = current, current + need
        if s_start <= now:
            current += step
            continue
        # To'liq oralik [s_start, s_end) hech qaysi band oralik bilan kesishmasin
        overlaps = any(s_start < iv_e and iv_s < s_end for iv_s, iv_e in intervals)
        if not overlaps:
            slots.append(s_start.time())
        current += step

    return slots


def create_appointment(*, client, barber, services, date, start_time) -> Appointment:
    """
    Bir yoki bir nechta xizmatли bron yaratadi (davomiylik = yig'indi).
    `services` — Service ro'yxati (kamida bittasi). Slot bo'sh emasligini tekshiradi.
    """
    services = list(services)
    if not services:
        raise ValueError("Kamida bitta xizmat tanlang.")

    total_duration = sum(s.duration for s in services)
    available = get_available_slots(barber, date, duration=total_duration)
    if start_time not in available:
        raise ValueError("Bu vaqt band yoki mavjud emas.")

    end_dt = datetime.combine(date, start_time) + timedelta(minutes=total_duration)

    appointment = Appointment.objects.create(
        client=client,
        barber=barber,
        service=services[0],           # asosiy (birinchi) xizmat
        shop=barber.shop,
        date=date,
        start_time=start_time,
        end_time=end_dt.time(),
        status=Appointment.Status.PENDING,
    )
    appointment.services.set(services)
    return appointment


#: Shu ko'p bekor qilishdan so'ng mijoz avtomatik bloklanadi (barberlarni himoya)
CANCEL_BLOCK_THRESHOLD = 3


def maybe_block_client(user):
    """Mijozning bekor qilingan bronlari sonini sanaydi; chegaradan (3) oshsa
    va hali bloklanmagan bo'lsa — avtomatik qora ro'yxatga oladi.
    (cancel_count, blocked_now) qaytaradi."""
    count = Appointment.objects.filter(
        client=user, status=Appointment.Status.CANCELLED
    ).count()
    blocked_now = False
    if count >= CANCEL_BLOCK_THRESHOLD and not user.is_blocked:
        user.is_blocked = True
        user.save(update_fields=["is_blocked"])
        blocked_now = True
    return count, blocked_now
