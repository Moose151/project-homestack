from django.contrib import admin

from apps.people.models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["display_name", "profile_type", "linked_user", "created_at"]
    list_filter = ["profile_type"]
    search_fields = ["display_name", "preferred_name"]
    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by", "deleted_at"]
