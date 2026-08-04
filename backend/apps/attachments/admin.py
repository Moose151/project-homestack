from django.contrib import admin

from apps.attachments.models import Attachment


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "uploaded_by",
        "linked_node",
        "visibility",
        "sensitivity",
        "created_at",
    ]
    list_filter = ["visibility", "sensitivity", "linked_node"]
    search_fields = ["original_filename", "linked_record_type", "checksum"]
    readonly_fields = ["filename", "file_size", "checksum", "created_at", "updated_at"]
