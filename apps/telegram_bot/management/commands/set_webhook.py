"""Telegram webhook'ni o'rnatadi yoki o'chiradi.

Foydalanish:
    python manage.py set_webhook            # TELEGRAM_WEBHOOK_URL ga o'rnatadi
    python manage.py set_webhook --delete   # webhook'ni o'chiradi
    python manage.py set_webhook --info      # joriy holatni ko'rsatadi
"""
import httpx
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Telegram webhook'ni o'rnatadi/o'chiradi (TELEGRAM_WEBHOOK_URL)."

    def add_arguments(self, parser):
        parser.add_argument("--delete", action="store_true", help="Webhook'ni o'chirish")
        parser.add_argument("--info", action="store_true", help="Joriy webhook holati")

    def handle(self, *args, **opts):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN sozlanmagan."))
            return
        base = f"https://api.telegram.org/bot{token}"

        if opts["info"]:
            r = httpx.get(f"{base}/getWebhookInfo", timeout=15)
            self.stdout.write(str(r.json()))
            return

        if opts["delete"]:
            r = httpx.post(f"{base}/deleteWebhook", timeout=15)
            self.stdout.write(self.style.WARNING(f"deleteWebhook: {r.json()}"))
            return

        url = settings.TELEGRAM_WEBHOOK_URL
        if not url:
            self.stderr.write(self.style.ERROR("TELEGRAM_WEBHOOK_URL sozlanmagan."))
            return

        payload = {
            "url": url,
            "allowed_updates": ["message", "callback_query", "channel_post"],
            "drop_pending_updates": True,
        }
        if settings.TELEGRAM_WEBHOOK_SECRET:
            payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET

        r = httpx.post(f"{base}/setWebhook", json=payload, timeout=15)
        data = r.json()
        if data.get("ok"):
            self.stdout.write(self.style.SUCCESS(f"Webhook o'rnatildi: {url}"))
        else:
            self.stderr.write(self.style.ERROR(f"Xatolik: {data}"))
