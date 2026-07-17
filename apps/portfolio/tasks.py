"""
Background task for syncing Telegram channel media to portfolio.
django-q2 orqali chaqiriladi.
"""
import logging
import httpx
from django.conf import settings

from apps.shops.models import Shop
from .models import PortfolioPost

logger = logging.getLogger(__name__)


def _save_post(shop: Shop, message: dict):
    """Parse a Telegram message and save as PortfolioPost."""
    photo = message.get("photo")
    video = message.get("video")

    if photo:
        largest = max(photo, key=lambda p: p.get("file_size", 0))
        file_id = largest["file_id"]
        file_unique_id = largest["file_unique_id"]
        file_type = PortfolioPost.FileType.PHOTO
        thumbnail_id = photo[0]["file_id"] if len(photo) > 1 else ""
    elif video:
        file_id = video["file_id"]
        file_unique_id = video["file_unique_id"]
        file_type = PortfolioPost.FileType.VIDEO
        thumb = video.get("thumbnail") or video.get("thumb")
        thumbnail_id = thumb["file_id"] if thumb else ""
    else:
        return

    PortfolioPost.objects.update_or_create(
        telegram_file_unique_id=file_unique_id,
        defaults={
            "shop": shop,
            "telegram_message_id": message["message_id"],
            "telegram_file_id": file_id,
            "file_type": file_type,
            "caption": message.get("caption", ""),
            "thumbnail_file_id": thumbnail_id,
        },
    )


def _sync_single_shop(shop: Shop):
    bot_api = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"
    resp = httpx.get(
        f"{bot_api}/getUpdates",
        params={"allowed_updates": ["channel_post"], "limit": 100},
        timeout=15,
    )
    if not resp.is_success:
        return

    channel_id = shop.telegram_channel_id
    for update in resp.json().get("result", []):
        post = update.get("channel_post", {})
        chat = post.get("chat", {})
        if str(chat.get("id")) == channel_id or chat.get("username") == channel_id.lstrip("@"):
            _save_post(shop, post)


def sync_telegram_channel(shop_id: str | None = None):
    """Sync media posts from Telegram channels for all active shops."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping sync.")
        return

    shops = Shop.objects.filter(is_active=True).exclude(telegram_channel_id="")
    if shop_id:
        shops = shops.filter(id=shop_id)

    for shop in shops:
        try:
            _sync_single_shop(shop)
        except Exception as exc:
            logger.error("Error syncing shop %s: %s", shop.id, exc)
