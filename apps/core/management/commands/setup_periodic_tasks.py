from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule


class Command(BaseCommand):
    help = "Set up default periodic tasks via django-q2 Schedule"

    def handle(self, *args, **options):
        # Re-engagement kuniga bir marta kunduzi 11:00 da ishlasin (tunda emas)
        now = timezone.localtime()
        reengage_run_at = now.replace(hour=11, minute=0, second=0, microsecond=0)
        if reengage_run_at <= now:
            reengage_run_at += timedelta(days=1)

        tasks = [
            {
                "name": "Send appointment reminders (5min)",
                "func": "apps.notifications.tasks.send_5min_reminders",
                "schedule_type": Schedule.MINUTES,
                "minutes": 1,
            },
            {
                "name": "Expire past appointments",
                "func": "apps.notifications.tasks.expire_appointments",
                "schedule_type": Schedule.MINUTES,
                "minutes": 5,
            },
            {
                "name": "Send appointment reminders (1h)",
                "func": "apps.notifications.tasks.send_upcoming_reminders",
                "schedule_type": Schedule.MINUTES,
                "minutes": 5,
            },
            {
                "name": "Send appointment reminders (24h)",
                "func": "apps.notifications.tasks.send_day_before_reminders",
                "schedule_type": Schedule.HOURLY,
            },
            {
                "name": "Sync Telegram portfolio channel",
                "func": "apps.portfolio.tasks.sync_telegram_channel",
                "schedule_type": Schedule.HOURLY,
            },
            {
                "name": "Re-engagement nudges (qaytmagan mijozlar)",
                "func": "apps.notifications.tasks.send_reengagement_nudges",
                "schedule_type": Schedule.DAILY,
                "next_run": reengage_run_at,
            },
        ]

        for t in tasks:
            name = t.pop("name")
            Schedule.objects.update_or_create(name=name, defaults=t)
            self.stdout.write(f"  ✓ {name}")

        self.stdout.write(self.style.SUCCESS("Periodic tasks configured."))
