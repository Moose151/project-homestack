from django.contrib import admin

from apps.home_wiki.models import WikiCategory, WikiPage


@admin.register(WikiCategory)
class WikiCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "is_hidden")
    search_fields = ("name",)
    list_filter = ("is_hidden",)


@admin.register(WikiPage)
class WikiPageAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_favourite", "is_emergency", "is_kiosk_safe", "visibility")
    search_fields = ("title", "body", "tags")
    list_filter = ("is_favourite", "is_emergency", "is_kiosk_safe", "visibility")
