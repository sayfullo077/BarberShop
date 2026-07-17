from django.contrib import admin
from .models import Appointment, BlockedSlot


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "barber", "service", "date", "start_time", "status", "created_at")
    list_filter = ("status", "date", "shop")
    search_fields = ("client__username", "barber__user__username", "service__name")
    date_hierarchy = "date"
    readonly_fields = ("created_at", "updated_at")
    actions = ["confirm_appointments", "cancel_appointments", "mark_completed"]

    @admin.action(description="Tasdiqlash")
    def confirm_appointments(self, request, queryset):
        for a in queryset.filter(status=Appointment.Status.PENDING):
            a.confirm()
        self.message_user(request, "Tasdiqlandi.")

    @admin.action(description="Bekor qilish")
    def cancel_appointments(self, request, queryset):
        for a in queryset.filter(status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]):
            a.cancel()
        self.message_user(request, "Bekor qilindi.")

    @admin.action(description="Bajarildi deb belgilash")
    def mark_completed(self, request, queryset):
        for a in queryset.filter(status=Appointment.Status.CONFIRMED):
            a.complete()
        self.message_user(request, "Bajarildi.")


@admin.register(BlockedSlot)
class BlockedSlotAdmin(admin.ModelAdmin):
    list_display = ("barber", "date", "start_time", "end_time", "reason")
    list_filter = ("barber__shop",)
    search_fields = ("barber__user__username",)
