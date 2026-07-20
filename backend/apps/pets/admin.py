from django.contrib import admin

from apps.pets.models import Pet, PetAppointment, PetTreatment


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "breed", "is_archived")
    search_fields = ("name", "breed", "vet_name")
    list_filter = ("species", "is_archived")


@admin.register(PetTreatment)
class PetTreatmentAdmin(admin.ModelAdmin):
    list_display = ("pet", "treatment_type", "name", "next_due_at", "last_done_at")
    search_fields = ("name", "notes")
    list_filter = ("treatment_type",)


@admin.register(PetAppointment)
class PetAppointmentAdmin(admin.ModelAdmin):
    list_display = ("pet", "display_title", "provider", "start_at")
    search_fields = ("title", "provider", "location", "notes")
