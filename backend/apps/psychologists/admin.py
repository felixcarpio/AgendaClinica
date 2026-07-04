from django.contrib import admin

from apps.accounts.models import Account
from .models import Psychologist


@admin.register(Psychologist)
class PsychologistAdmin(admin.ModelAdmin):
    list_display = ("account", "license_number")
    search_fields = ("account__email", "account__first_name", "account__last_name", "license_number")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "account":
            kwargs["queryset"] = Account.objects.filter(role=Account.Role.PSYCHOLOGIST)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)