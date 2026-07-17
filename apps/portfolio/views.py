from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.conf import settings
import httpx

from .models import PortfolioPost
from apps.shops.models import Shop


@require_GET
def portfolio_api(request, shop_slug):
    """Returns paginated portfolio posts for a shop with Telegram file URLs."""
    shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
    page = int(request.GET.get("page", 1))
    per_page = 12
    offset = (page - 1) * per_page

    posts = PortfolioPost.objects.filter(
        shop=shop, is_active=True
    ).values(
        "id", "telegram_file_id", "thumbnail_file_id",
        "file_type", "caption", "created_at"
    )[offset: offset + per_page]

    data = []
    for post in posts:
        file_url = _get_file_url(post["thumbnail_file_id"] or post["telegram_file_id"])
        data.append({
            "id": str(post["id"]),
            "file_type": post["file_type"],
            "caption": post["caption"],
            "url": file_url,
        })

    total = PortfolioPost.objects.filter(shop=shop, is_active=True).count()
    return JsonResponse({"posts": data, "total": total, "page": page})


def _get_file_url(file_id: str) -> str | None:
    """Get a temporary download URL from Telegram Bot API."""
    if not file_id or not settings.TELEGRAM_BOT_TOKEN:
        return None
    try:
        resp = httpx.get(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=5,
        )
        if resp.is_success:
            path = resp.json()["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{path}"
    except Exception:
        pass
    return None
