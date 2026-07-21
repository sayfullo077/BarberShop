"""
Bron mantiqi testlari — slot generatsiyasi va bron yaratish.
Bu modul avval real overlap bug bo'lgan joy (faqat aniq start_time collision
tekshirilardi) — regressiyani ushlab turadi.
"""
from datetime import date, time, timedelta

from django.test import TestCase

from apps.bookings.models import Appointment, BlockedSlot
from apps.bookings.services import get_available_slots, create_appointment
from apps.core.test_utils import (
    make_shop, make_barber, make_service, make_client, set_working_hours,
    make_appointment,
)


def _tomorrow():
    """Testlar kelajakdagi sanani ishlatadi — o'tgan slotlar filtrlanmasin."""
    return date.today() + timedelta(days=1)


class AvailableSlotsTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        self.barber = make_barber(self.shop, slot_duration=30)
        self.day = _tomorrow()
        set_working_hours(self.shop, self.day.weekday(), open_h=9, close_h=12)

    def test_day_off_returns_empty(self):
        # 9-12 ish vaqti bor edi, endi dam kuni deb belgilaymiz
        self.shop.working_hours.all().delete()
        set_working_hours(self.shop, self.day.weekday(), day_off=True)
        self.assertEqual(get_available_slots(self.barber, self.day), [])

    def test_no_working_hours_returns_empty(self):
        self.shop.working_hours.all().delete()
        self.assertEqual(get_available_slots(self.barber, self.day), [])

    def test_full_day_slots(self):
        # 9:00–12:00, 30 daq → 09:00,09:30,10:00,10:30,11:00,11:30 (11:30+30=12:00 <= 12:00)
        slots = get_available_slots(self.barber, self.day)
        self.assertEqual(
            slots,
            [time(9, 0), time(9, 30), time(10, 0), time(10, 30), time(11, 0), time(11, 30)],
        )

    def test_existing_booking_blocks_overlapping_slots(self):
        client = make_client()
        svc = make_service(self.shop, duration=30)
        Appointment.objects.create(
            client=client, barber=self.barber, service=svc, shop=self.shop,
            date=self.day, start_time=time(10, 0), end_time=time(10, 30),
            status=Appointment.Status.CONFIRMED,
        )
        slots = get_available_slots(self.barber, self.day)
        self.assertNotIn(time(10, 0), slots)
        self.assertIn(time(9, 30), slots)   # 09:30–10:00 tegib turadi, ochiq
        self.assertIn(time(10, 30), slots)

    def test_long_duration_partial_overlap_is_blocked(self):
        """REGRESSIYA: eski bug — 09:30 boshlangan 60-daqiqalik slot 10:00 dagi
        bron ichiga kirib ketardi (aniq start_time mos kelmagani uchun o'tib ketardi).
        Endi to'liq oralik overlap bloklashi kerak."""
        client = make_client()
        svc = make_service(self.shop, duration=30)
        Appointment.objects.create(
            client=client, barber=self.barber, service=svc, shop=self.shop,
            date=self.day, start_time=time(10, 0), end_time=time(10, 30),
            status=Appointment.Status.CONFIRMED,
        )
        slots = get_available_slots(self.barber, self.day, duration=60)
        # 09:30–10:30 bron (10:00–10:30) bilan kesishadi → bo'lmasligi kerak
        self.assertNotIn(time(9, 30), slots)
        # 09:00–10:00 tegib turadi, kesishmaydi → ochiq
        self.assertIn(time(9, 0), slots)

    def test_cancelled_booking_does_not_block(self):
        client = make_client()
        svc = make_service(self.shop, duration=30)
        Appointment.objects.create(
            client=client, barber=self.barber, service=svc, shop=self.shop,
            date=self.day, start_time=time(10, 0), end_time=time(10, 30),
            status=Appointment.Status.CANCELLED,
        )
        # Bekor qilingan bron band hisoblanmaydi (ACTIVE_STATUSES emas)
        self.assertIn(time(10, 0), get_available_slots(self.barber, self.day))

    def test_blocked_slot_removes_availability(self):
        BlockedSlot.objects.create(
            barber=self.barber, date=self.day,
            start_time=time(11, 0), end_time=time(11, 30),
        )
        self.assertNotIn(time(11, 0), get_available_slots(self.barber, self.day))

    def test_duration_longer_than_workday_yields_no_slots(self):
        # 3 soatlik ish kuni, 4 soatlik xizmat → hech qanday slot sig'maydi
        self.assertEqual(get_available_slots(self.barber, self.day, duration=240), [])


class CreateAppointmentTests(TestCase):
    def setUp(self):
        self.shop = make_shop()
        self.barber = make_barber(self.shop, slot_duration=30)
        self.client_user = make_client()
        self.day = _tomorrow()
        set_working_hours(self.shop, self.day.weekday(), open_h=9, close_h=18)

    def test_requires_at_least_one_service(self):
        with self.assertRaises(ValueError):
            create_appointment(
                client=self.client_user, barber=self.barber,
                services=[], date=self.day, start_time=time(9, 0),
            )

    def test_rejects_unavailable_time(self):
        svc = make_service(self.shop, duration=30)
        with self.assertRaises(ValueError):
            create_appointment(
                client=self.client_user, barber=self.barber,
                services=[svc], date=self.day, start_time=time(3, 0),  # ish vaqtidan tashqari
            )

    def test_creates_with_summed_duration_and_end_time(self):
        s1 = make_service(self.shop, duration=30)
        s2 = make_service(self.shop, duration=45)
        appt = create_appointment(
            client=self.client_user, barber=self.barber,
            services=[s1, s2], date=self.day, start_time=time(9, 0),
        )
        self.assertEqual(appt.end_time, time(10, 15))       # 09:00 + 75 daq
        self.assertEqual(appt.service, s1)                   # asosiy = birinchi
        self.assertEqual(set(appt.services.all()), {s1, s2})
        self.assertEqual(appt.status, Appointment.Status.PENDING)

    def test_double_booking_same_slot_is_rejected(self):
        svc = make_service(self.shop, duration=30)
        create_appointment(
            client=self.client_user, barber=self.barber,
            services=[svc], date=self.day, start_time=time(9, 0),
        )
        with self.assertRaises(ValueError):
            create_appointment(
                client=make_client(), barber=self.barber,
                services=[svc], date=self.day, start_time=time(9, 0),
            )


class CancelBlockTests(TestCase):
    """Ko'p bekor qilgan mijoz avtomatik qora ro'yxatga olinadi (barberlarni himoya)."""

    def setUp(self):
        from apps.bookings.services import CANCEL_BLOCK_THRESHOLD
        self.threshold = CANCEL_BLOCK_THRESHOLD
        self.barber = make_barber()
        self.client_user = make_client()

    def _cancelled(self, n):
        for _ in range(n):
            make_appointment(
                client=self.client_user, barber=self.barber, shop=self.barber.shop,
                status=Appointment.Status.CANCELLED,
            )

    def test_blocks_after_threshold(self):
        from apps.bookings.services import maybe_block_client
        self._cancelled(self.threshold)
        count, blocked = maybe_block_client(self.client_user)
        self.assertEqual(count, self.threshold)
        self.assertTrue(blocked)
        self.client_user.refresh_from_db()
        self.assertTrue(self.client_user.is_blocked)

    def test_not_blocked_below_threshold(self):
        from apps.bookings.services import maybe_block_client
        self._cancelled(self.threshold - 1)
        count, blocked = maybe_block_client(self.client_user)
        self.assertFalse(blocked)
        self.client_user.refresh_from_db()
        self.assertFalse(self.client_user.is_blocked)

    def test_idempotent_when_already_blocked(self):
        from apps.bookings.services import maybe_block_client
        self._cancelled(self.threshold + 2)
        self.client_user.is_blocked = True
        self.client_user.save(update_fields=["is_blocked"])
        count, blocked = maybe_block_client(self.client_user)
        self.assertFalse(blocked)   # allaqachon bloklangan — qayta bloklamaydi


class FavoriteModelTests(TestCase):
    def test_unique_together(self):
        from django.db import IntegrityError, transaction
        from apps.shops.models import Favorite
        c = make_client()
        shop = make_shop()
        Favorite.objects.create(client=c, shop=shop)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Favorite.objects.create(client=c, shop=shop)
