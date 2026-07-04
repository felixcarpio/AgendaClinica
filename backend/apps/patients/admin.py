from django.contrib import admin

from apps.accounts.models import Account
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("account",)
    search_fields = ("account__email", "account__first_name", "account__last_name")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "account":
            kwargs["queryset"] = Account.objects.filter(role=Account.Role.PATIENT)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)