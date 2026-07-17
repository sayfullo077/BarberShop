"""Telegram botni polling (long-polling) rejimida ishga tushiradi.

Webhook o'rniga getUpdates ishlatiladi — bot uchun HTTPS/webhook sozlash shart emas.
    python manage.py run_bot
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Telegram botni polling rejimida ishga tushiradi (webhook o'rniga)."

    def handle(self, *args, **opts):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN sozlanmagan."))
            return

        # Bot bitta event loop'da ishlaydi — handler'lar ichida Django ORM'ga ruxsat.
        os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

        # Polling webhook bilan bir vaqtda ishlamaydi (getUpdates 409 beradi) —
        # avval mavjud webhook'ni o'chiramiz.
        import httpx
        try:
            httpx.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/deleteWebhook",
                json={"drop_pending_updates": False},
                timeout=15,
            )
        except Exception as e:  # noqa: BLE001
            self.stderr.write(f"deleteWebhook ogohlantirish: {e}")

        from apps.telegram_bot.bot import build_application

        app = build_application()
        self.stdout.write(self.style.SUCCESS("🤖 Bot polling rejimida ishga tushdi."))
        app.run_polling(
            allowed_updates=["message", "callback_query", "channel_post"],
            drop_pending_updates=True,
        )
