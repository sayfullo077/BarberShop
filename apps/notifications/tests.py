"""Re-engagement («vaqt keldi») eslatma taski uchun testlar."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Appointment
from apps.notifications.models import NotificationLog
from apps.notifications.tasks import send_reengagement_nudges, REENGAGE_AFTER_DAYS
from apps.core.test_utils import make_client, make_barber, make_appointment


class ReengagementTests(TestCase):
    def setUp(self):
        self.barber = make_barber()
        self.today = timezone.localdate()
        self.old = self.today - timedelta(days=REENGAGE_AFTER_DAYS + 10)
        self.recent = self.today - timedelta(days=5)

    def _appt(self, client, date, status=Appointment.Status.COMPLETED):
        return make_appointment(client=client, barber=self.barber,
                                shop=self.barber.shop, date=date, status=status)

    def test_nudges_lapsed_client(self):
        c = make_client()
        self._appt(c, self.old)
        sent = send_reengagement_nudges()
        self.assertEqual(sent, 1)
        c.refresh_from_db()
        self.assertIsNotNone(c.last_reengaged_at)
        self.assertTrue(NotificationLog.objects.filter(
            user=c, notification_type="reengagement").exists())

    def test_skips_recent_visitor(self):
        c = make_client()
        self._appt(c, self.recent)
        self.assertEqual(send_reengagement_nudges(), 0)

    def test_skips_client_with_future_booking(self):
        c = make_client()
        self._appt(c, self.old)
        # kelgusi faol bron
        self._appt(c, self.today + timedelta(days=2), status=Appointment.Status.CONFIRMED)
        self.assertEqual(send_reengagement_nudges(), 0)

    def test_cooldown_prevents_repeat(self):
        c = make_client()
        self._appt(c, self.old)
        self.assertEqual(send_reengagement_nudges(), 1)
        # ikkinchi chaqiruv — cooldown ichida, qayta yubormaydi
        self.assertEqual(send_reengagement_nudges(), 0)

    def test_skips_client_without_telegram(self):
        c = make_client(telegram_id=None)
        self._appt(c, self.old)
        self.assertEqual(send_reengagement_nudges(), 0)

    def test_only_cancelled_history_not_nudged(self):
        # COMPLETED tashrifi yo'q (faqat bekor qilingan) — «tashrif buyurgan» emas
        c = make_client()
        self._appt(c, self.old, status=Appointment.Status.CANCELLED)
        self.assertEqual(send_reengagement_nudges(), 0)
