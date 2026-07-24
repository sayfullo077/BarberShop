"""
Low-level notification senders: Telegram and SMS (Eskiz.uz).
"""
import logging
import httpx
from django.conf import settings
from django.utils import timezone

from .models import NotificationLog

logger = logging.getLogger(__name__)

BOT_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"

ESKIZ_TOKEN_CACHE: dict[str, str] = {}


def send_telegram_message(telegram_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Send a Telegram message to a user by their telegram_id."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("No TELEGRAM_BOT_TOKEN configured.")
        return False
    try:
        resp = httpx.post(
            f"{BOT_API}/sendMessage",
            json={"chat_id": telegram_id, "text": text, "parse_mode": parse_mode},
            timeout=10,
        )
        return resp.is_success and resp.json().get("ok")
    except Exception as e:
        logger.error("Telegram send error: %s", e)
        return False


def send_telegram_document(telegram_id, file_path: str, caption: str = "") -> bool:
    """Faylni Telegram orqali yuboradi (sendDocument, ≤50MB bot chegarasi)."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("No TELEGRAM_BOT_TOKEN configured.")
        return False
    try:
        with open(file_path, "rb") as fh:
            resp = httpx.post(
                f"{BOT_API}/sendDocument",
                data={"chat_id": telegram_id, "caption": caption, "parse_mode": "HTML"},
                files={"document": fh},
                timeout=180,
            )
        return resp.is_success and resp.json().get("ok")
    except Exception as e:
        logger.error("Telegram document send error: %s", e)
        return False


def _get_eskiz_token() -> str | None:
    """Authenticate with Eskiz.uz and return bearer token."""
    if ESKIZ_TOKEN_CACHE.get("token"):
        return ESKIZ_TOKEN_CACHE["token"]
    try:
        resp = httpx.post(
            "https://notify.eskiz.uz/api/auth/login",
            data={"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD},
            timeout=10,
        )
        if resp.is_success:
            token = resp.json()["data"]["token"]
            ESKIZ_TOKEN_CACHE["token"] = token
            return token
    except Exception as e:
        logger.error("Eskiz auth error: %s", e)
    return None


def send_sms(phone: str, message: str) -> bool:
    """Send SMS via Eskiz.uz API."""
    if not settings.ESKIZ_EMAIL:
        logger.warning("Eskiz credentials not configured.")
        return False
    token = _get_eskiz_token()
    if not token:
        return False
    try:
        resp = httpx.post(
            "https://notify.eskiz.uz/api/message/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "mobile_phone": phone.replace("+", ""),
                "message": message,
                "from": "4546",
            },
            timeout=10,
        )
        return resp.is_success
    except Exception as e:
        logger.error("SMS send error: %s", e)
        return False


def notify_user(user, message: str, appointment=None, notification_type: str = "custom"):
    """
    Send notification via Telegram (preferred) or SMS fallback.
    Logs the result to NotificationLog.
    """
    channel = NotificationLog.Channel.TELEGRAM
    success = False
    error = ""

    if user.telegram_id:
        success = send_telegram_message(user.telegram_id, message)
        if not success:
            error = "Telegram yetkazib berilmadi"
    elif user.phone:
        channel = NotificationLog.Channel.SMS
        success = send_sms(user.phone, message)
        if not success:
            error = "SMS yetkazib berilmadi"

    NotificationLog.objects.create(
        user=user,
        appointment=appointment,
        notification_type=notification_type,
        channel=channel,
        message=message,
        is_sent=success,
        sent_at=timezone.now() if success else None,
        error=error,
    )
    return success
