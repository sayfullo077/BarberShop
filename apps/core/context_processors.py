from django.conf import settings


def site_settings(request):
    return {
        "TELEGRAM_BOT_TOKEN": settings.TELEGRAM_BOT_TOKEN,
        "SITE_NAME": "BarberShop",
    }
