"""
Booking business logic — slot generation and availability checks.
"""
from datetime import datetime, timedelta, time, date as date_type
from typing import List

from django.db.models import Q

from .models import Appointment, BlockedSlot
from apps.shops.models import BarberProfile, WorkingHours


def get_available_slots(barber: BarberProfile, date: date_type) -> List[time]:
    """
    Returns list of available start times for a given barber and date.
    Considers: working hours, existing appointments, blocked slots.
    """
    day_of_week = date.weekday()

    try:
        wh = WorkingHours.objects.get(shop=barber.shop, day_of_week=day_of_week)
    except WorkingHours.DoesNotExist:
        return []

    if wh.is_day_off:
        return []

    slot_delta = timedelta(minutes=barber.slot_duration)
    slots = []
    current = datetime.combine(date, wh.open_time)
    end_of_day = datetime.combine(date, wh.close_time)

    booked = set(
        Appointment.objects.filter(
            barber=barber,
            date=date,
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
        ).values_list("start_time", flat=True)
    )

    blocked = list(
        BlockedSlot.objects.filter(barber=barber, date=date).values("start_time", "end_time")
    )

    now = datetime.now()

    while current + slot_delta <= end_of_day:
        slot_time = current.time()

        # Skip past slots
        if datetime.combine(date, slot_time) <= now:
            current += slot_delta
            continue

        # Skip booked
        if slot_time in booked:
            current += slot_delta
            continue

        # Skip blocked
        overlaps_block = any(
            b["start_time"] <= slot_time < b["end_time"] for b in blocked
        )
        if overlaps_block:
            current += slot_delta
            continue

        slots.append(slot_time)
        current += slot_delta

    return slots


def create_appointment(*, client, barber, service, date, start_time) -> Appointment:
    """
    Creates an appointment after validating slot availability.
    Raises ValueError if the slot is not available.
    """
    available = get_available_slots(barber, date)
    if start_time not in available:
        raise ValueError("Bu vaqt band yoki mavjud emas.")

    end_dt = datetime.combine(date, start_time) + timedelta(minutes=service.duration)

    appointment = Appointment.objects.create(
        client=client,
        barber=barber,
        service=service,
        shop=barber.shop,
        date=date,
        start_time=start_time,
        end_time=end_dt.time(),
        status=Appointment.Status.PENDING,
    )
    return appointment
