from django.contrib import admin
from .models import Shop, WorkingHours, BarberProfile


class WorkingHoursInline(admin.TabularInline):
    model = WorkingHours
    extra = 0


class BarberProfileInline(admin.TabularInline):
    model = BarberProfile
    extra = 0
    fields = ("user", "experience_years", "slot_duration", "is_accepting_bookings", "order")


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "phone", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "address", "phone", "owner__username")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [WorkingHoursInline, BarberProfileInline]
    fieldsets = (
        (None, {"fields": ("owner", "name", "slug", "description", "is_active")}),
        ("Aloqa", {"fields": ("phone", "address", "telegram_channel_id", "instagram_url", "telegram_url")}),
        ("Rasm", {"fields": ("logo", "cover")}),
        ("Joylashuv", {"fields": ("latitude", "longitude"), "classes": ("collapse",)}),
    )


@admin.register(BarberProfile)
class BarberProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "shop", "experience_years", "slot_duration", "is_accepting_bookings")
    list_filter = ("shop", "is_accepting_bookings")
    search_fields = ("user__username", "user__first_name", "shop__name")


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ("shop", "day_of_week", "open_time", "close_time", "is_day_off")
    list_filter = ("shop", "is_day_off")
