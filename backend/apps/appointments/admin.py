from django.contrib import admin
from .models import AvailabilitySlot, Appointment
from django import forms
from django.db.models import Q


class AppointmentAdminForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        queryset = AvailabilitySlot.objects.filter(
            status=AvailabilitySlot.Status.AVAILABLE
        )

        if self.instance and self.instance.pk:
            queryset = AvailabilitySlot.objects.filter(
                Q(status=AvailabilitySlot.Status.AVAILABLE) |
                Q(pk=self.instance.availability_slot.pk)
            )

        self.fields["availability_slot"].queryset = queryset



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
    form = AppointmentAdminForm
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