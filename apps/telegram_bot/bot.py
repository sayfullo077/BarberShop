"""
Telegram Bot handlers.
Handles: /start, /bekor_<id>, inline keyboard for booking cancellation,
and channel_post for portfolio sync.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from django.conf import settings

logger = logging.getLogger(__name__)


def _webapp_url() -> str:
    """WebApp (mini-ilova) manzili — TELEGRAM_WEBAPP_URL yoki webhook origin'i."""
    from urllib.parse import urlparse
    explicit = getattr(settings, "TELEGRAM_WEBAPP_URL", "")
    if explicit:
        return explicit
    p = urlparse(settings.TELEGRAM_WEBHOOK_URL or "")
    if p.scheme and p.netloc:
        return f"{p.scheme}://{p.netloc}/"
    return settings.TELEGRAM_WEBHOOK_URL or ""


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    webapp_url = _webapp_url()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "💈 Bron qilish",
            web_app={"url": webapp_url},
        )]
    ])
    await update.message.reply_html(
        f"Salom, <b>{user.first_name}</b>! 💈\n\n"
        f"Men BarberShop bronlash botiman.\n"
        f"Quyidagi tugma orqali onlayn bron qiling:",
        reply_markup=keyboard,
    )


async def cancel_booking_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle /bekor_<uuid> command."""
    command = update.message.text
    appointment_id = command.replace("/bekor_", "").strip()

    from apps.bookings.models import Appointment
    try:
        appt = Appointment.objects.select_related("client").get(
            id=appointment_id,
            client__telegram_id=update.effective_user.id,
        )
    except Appointment.DoesNotExist:
        await update.message.reply_text("Bron topilmadi.")
        return

    if appt.status not in (Appointment.Status.PENDING, Appointment.Status.CONFIRMED):
        await update.message.reply_text("Bu bron allaqachon bekor qilingan yoki bajarilgan.")
        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Ha, bekor qiling", callback_data=f"cancel:{appointment_id}"),
            InlineKeyboardButton("❌ Yo'q", callback_data="noop"),
        ]
    ])
    await update.message.reply_text(
        f"📅 {appt.date.strftime('%d.%m.%Y')} {appt.start_time.strftime('%H:%M')} bronini bekor qilmoqchimisiz?",
        reply_markup=keyboard,
    )


async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "noop":
        await query.edit_message_text("Bekor qilinmadi.")
        return

    if query.data.startswith("cancel:"):
        appointment_id = query.data.split(":", 1)[1]
        from apps.bookings.models import Appointment
        from django_q.tasks import async_task
        try:
            appt = Appointment.objects.get(
                id=appointment_id,
                client__telegram_id=update.effective_user.id,
            )
            appt.cancel()
            async_task("apps.notifications.tasks.send_cancellation_notice", appointment_id)
            await query.edit_message_text("✅ Bron bekor qilindi.")
        except Appointment.DoesNotExist:
            await query.edit_message_text("Bron topilmadi.")


async def handle_channel_post(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Sync portfolio posts from connected Telegram channels."""
    post = update.channel_post
    if not post:
        return

    from apps.shops.models import Shop
    from apps.portfolio.tasks import _save_post

    channel_id = str(post.chat.id)
    channel_username = f"@{post.chat.username}" if post.chat.username else None

    shop = (
        Shop.objects.filter(telegram_channel_id=channel_id).first()
        or (
            Shop.objects.filter(telegram_channel_id=channel_username).first()
            if channel_username else None
        )
    )

    if shop and (post.photo or post.video):
        _save_post(shop, post.to_dict())


async def handle_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi kontakt (telefon) ulashganда — raqamни tasdiqlaymiz.
    (WebApp `requestContact` kontaktni botga yuboradi — ishonchli tasdiq yo'li.)"""
    contact = update.message.contact if update.message else None
    if not contact:
        return
    # Faqat o'zining raqamini ulashganда (boshqasinikini emas)
    if contact.user_id and contact.user_id != update.effective_user.id:
        return

    from apps.accounts.models import User
    u = User.objects.filter(telegram_id=update.effective_user.id).first()
    if u:
        u.phone = (contact.phone_number or "")[:20]
        u.phone_verified = True
        u.save(update_fields=["phone", "phone_verified"])
        await update.message.reply_text(
            "✅ Raqamingiz tasdiqlandi! Ilovaga qaytishingiz mumkin."
        )


def build_application() -> Application:
    application = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .build()
    )
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.Regex(r"^/bekor_"), cancel_booking_command)
    )
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(
        MessageHandler(filters.ChatType.CHANNEL, handle_channel_post)
    )
    return application
