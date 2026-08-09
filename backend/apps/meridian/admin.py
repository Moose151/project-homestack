from django.contrib import admin

from apps.meridian.models import (
    MeridianCategory,
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianTask,
)


@admin.register(MeridianCategory)
class MeridianCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "position")


@admin.register(MeridianTask)
class MeridianTaskAdmin(admin.ModelAdmin):
    # A M2M cannot appear in list_display; assignees are edited on the detail page.
    list_display = ("title", "status", "points", "is_hot", "due_at")
    filter_horizontal = ("assigned_to_people",)
    list_filter = ("status", "is_hot")
    search_fields = ("title", "description")


@admin.register(MeridianReward)
class MeridianRewardAdmin(admin.ModelAdmin):
    list_display = ("name", "cost_points", "is_active")
    list_filter = ("is_active",)


@admin.register(MeridianRewardRequest)
class MeridianRewardRequestAdmin(admin.ModelAdmin):
    list_display = ("reward", "requested_by_person", "status", "points_spent")
    list_filter = ("status",)


@admin.register(MeridianPointsEntry)
class MeridianPointsEntryAdmin(admin.ModelAdmin):
    list_display = ("person", "points", "reason", "created_at")
