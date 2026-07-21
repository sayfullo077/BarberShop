from django.contrib import admin
from .models import Shop, WorkingHours, BarberProfile, Report, Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("client", "shop", "created_at")
    search_fields = ("client__username", "shop__name")


class WorkingHoursInline(admin.TabularInline):
    model = WorkingHours
    extra = 0


class BarberProfileInline(admin.TabularInline):
    model = BarberProfile
    extra = 0
    fields = ("user", "experience_years", "slot_duration", "is_accepting_bookings", "order")


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "phone", "is_active", "is_suspended", "rating_avg", "created_at")
    list_filter = ("is_active", "is_suspended")
    search_fields = ("name", "address", "phone", "owner__username")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [WorkingHoursInline, BarberProfileInline]
    actions = ["suspend_shops", "unsuspend_shops"]
    fieldsets = (
        (None, {"fields": ("owner", "name", "slug", "description", "is_active", "is_suspended")}),
        ("Aloqa", {"fields": ("phone", "address", "city", "telegram_channel_id",
                              "instagram_url", "telegram_url", "facebook_url", "tiktok_url", "youtube_url")}),
        ("Rasm", {"fields": ("logo", "cover")}),
        ("Joylashuv", {"fields": ("latitude", "longitude"), "classes": ("collapse",)}),
    )

    @admin.action(description="To'xtatish (yashirish)")
    def suspend_shops(self, request, queryset):
        n = queryset.update(is_suspended=True)
        self.message_user(request, f"{n} ta salon to'xtatildi.")

    @admin.action(description="Tiklash (ko'rsatish)")
    def unsuspend_shops(self, request, queryset):
        n = queryset.update(is_suspended=False)
        self.message_user(request, f"{n} ta salon tiklandi.")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("shop", "reporter", "reason", "status", "created_at")
    list_filter = ("status", "reason", "shop")
    search_fields = ("shop__name", "reporter__username", "comment")
    readonly_fields = ("created_at", "updated_at")
    actions = ["suspend_shop", "block_owner", "dismiss_reports"]

    @admin.action(description="Salonni to'xtatish + ko'rib chiqilgan")
    def suspend_shop(self, request, queryset):
        for r in queryset:
            r.shop.is_suspended = True
            r.shop.save(update_fields=["is_suspended"])
            queryset.model.objects.filter(pk=r.pk).update(status=Report.Status.REVIEWED)
        self.message_user(request, "Salon(lar) to'xtatildi.")

    @admin.action(description="Salon egasini BLOKLASH")
    def block_owner(self, request, queryset):
        for r in queryset.select_related("shop__owner"):
            u = r.shop.owner
            u.is_blocked = True
            u.save(update_fields=["is_blocked"])
        queryset.update(status=Report.Status.REVIEWED)
        self.message_user(request, "Egalar bloklandi (ularning salonlari yashirinadi).")

    @admin.action(description="Rad etish (asossiz shikoyat)")
    def dismiss_reports(self, request, queryset):
        shops = {r.shop for r in queryset}
        queryset.update(status=Report.Status.DISMISSED)
        # Ochiq shikoyatlar qolmagan salonlarni tiklaymiz
        for shop in shops:
            if not Report.objects.filter(shop=shop, status=Report.Status.OPEN).exists():
                shop.is_suspended = False
                shop.save(update_fields=["is_suspended"])
        self.message_user(request, "Shikoyat(lar) rad etildi va salonlar tiklandi.")


@admin.register(BarberProfile)
class BarberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "shop", "experience_years", "slot_duration", "is_accepting_bookings")
    list_filter = ("shop", "is_accepting_bookings")
    search_fields = ("user__username", "user__first_name", "shop__name")


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ("shop", "day_of_week", "open_time", "close_time", "is_day_off")
    list_filter = ("shop", "is_day_off")
