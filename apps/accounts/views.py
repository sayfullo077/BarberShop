import hashlib
import hmac
import json
import time
from urllib.parse import unquote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import User


def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")
    return render(request, "pages/login.html")


@require_POST
def telegram_auth(request):
    """Telegram Login Widget callback."""
    data = request.POST.dict()
    received_hash = data.pop("hash", None)
    if not received_hash:
        return JsonResponse({"error": "No hash"}, status=400)

    # Check auth_date not older than 1 day
    auth_date = int(data.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        return JsonResponse({"error": "Auth data expired"}, status=400)

    # Verify hash
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode()).digest()
    computed_hash = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return JsonResponse({"error": "Invalid hash"}, status=400)

    telegram_id = int(data["id"])
    user, created = User.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={
            "username": data.get("username") or f"tg_{telegram_id}",
            "first_name": data.get("first_name", ""),
            "last_name": data.get("last_name", ""),
            "telegram_username": data.get("username", ""),
            "is_telegram_verified": True,
        },
    )
    if not created:
        user.telegram_username = data.get("username", "")
        user.is_telegram_verified = True
        user.save(update_fields=["telegram_username", "is_telegram_verified"])

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return JsonResponse({"ok": True, "redirect": "/"})


@login_required
def profile_view(request):
    return render(request, "pages/profile.html", {"user": request.user})


def logout_view(request):
    logout(request)
    return redirect("/")
