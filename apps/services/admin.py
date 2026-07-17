from django.contrib import admin
from .models import Service, ServiceCategory


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 0
    fields = ("name", "duration", "price", "is_active", "order")


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "shop", "order")
    list_filter = ("shop",)
    search_fields = ("name", "shop__name")
    inlines = [ServiceInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "shop", "category", "duration", "price", "is_active")
    list_filter = ("shop", "is_active", "category")
    search_fields = ("name", "shop__name")
    filter_horizontal = ("barbers",)
    list_editable = ("is_active", "price")
