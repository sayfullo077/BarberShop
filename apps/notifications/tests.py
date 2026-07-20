"""Re-engagement («vaqt keldi») eslatma taski uchun testlar."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.bookings.models import Appointment, WaitlistEntry
from apps.notifications.models import NotificationLog
from apps.notifications.tasks import (
    send_reengagement_nudges, REENGAGE_AFTER_DAYS, notify_waitlist,
)
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


class WaitlistNotifyTests(TestCase):
    """Joy bo'shaganda navbatdagilarga xabar (notify_waitlist)."""

    def setUp(self):
        self.barber = make_barber()
        self.date = timezone.localdate() + timedelta(days=2)

    def _entry(self, *, client=None, notified=False, date=None):
        return WaitlistEntry.objects.create(
            client=client or make_client(), barber=self.barber,
            date=date or self.date, notified=notified,
        )

    def test_notifies_all_waiting_clients(self):
        e1 = self._entry()
        self._entry()
        sent = notify_waitlist(str(self.barber.id), self.date.isoformat())
        self.assertEqual(sent, 2)
        e1.refresh_from_db()
        self.assertTrue(e1.notified)
        self.assertTrue(NotificationLog.objects.filter(
            user=e1.client, notification_type="waitlist_freed").exists())

    def test_skips_already_notified(self):
        self._entry(notified=True)
        self.assertEqual(notify_waitlist(str(self.barber.id), self.date.isoformat()), 0)

    def test_skips_past_date(self):
        past = timezone.localdate() - timedelta(days=1)
        self._entry(date=past)
        self.assertEqual(notify_waitlist(str(self.barber.id), past.isoformat()), 0)

    def test_duplicate_entry_blocked(self):
        from django.db import IntegrityError, transaction
        c = make_client()
        self._entry(client=c)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._entry(client=c)
