"""
Telegram Bot webhook + WebApp HTML entry point.
"""
import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from telegram import Update

logger = logging.getLogger(__name__)


async def _process_update(data: dict):
    """Application'ni to'g'ri initialize qilib update'ni qayta ishlaydi.
    (PTB v21: initialize() chaqirilmasa process_update RuntimeError beradi.)"""
    from .bot import build_application
    app = build_application()
    await app.initialize()
    try:
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
    finally:
        await app.shutdown()


@csrf_exempt
@require_POST
def webhook(request):
    """Receive updates from Telegram via webhook."""
    if settings.TELEGRAM_WEBHOOK_SECRET:
        token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if token != settings.TELEGRAM_WEBHOOK_SECRET:
            return HttpResponse(status=403)

    if not settings.TELEGRAM_BOT_TOKEN:
        return HttpResponse(status=503)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    import asyncio
    try:
        asyncio.run(_process_update(data))
    except Exception:
        logger.exception("Webhook update qayta ishlashda xatolik")
    # Telegram'ga har doim 200 qaytaramiz (aks holda u update'ni qayta yuboraveradi)
    return HttpResponse("ok")


def webapp_index(request):
    """Serve the Telegram WebApp SPA."""
    return render(request, "telegram/webapp.html", {
        "BOT_TOKEN": settings.TELEGRAM_BOT_TOKEN,
        "DEBUG": settings.DEBUG,
    })
