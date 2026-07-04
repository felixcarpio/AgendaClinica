from django.contrib import admin
from .models import AvailabilitySlot, Appointment


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = (
        "psychologist",
        "start_time",
        "end_time",
        "status",
        "created_at",
    )
    list_filter = ("status", "psychologist")
    search_fields = (
        "psychologist__account__first_name",
        "psychologist__account__last_name",
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "patient",
        "psychologist",
        "availability_slot",
        "status",
        "created_at",
    )
    list_filter = ("status", "psychologist", "patient")
    search_fields = (
        "patient__account__first_name",
        "patient__account__last_name",
        "psychologist__account__first_name",
        "psychologist__account__last_name",
    )