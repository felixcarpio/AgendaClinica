from django.contrib import admin

from apps.accounts.models import Account
from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """
    Configuración administrativa para los pacientes.

    Permite consultar, buscar y filtrar pacientes según
    su estado dentro del proceso clínico.
    """

    list_display = (
        "account",
        "status",
        "phone",
        "created_at",
    )

    list_filter = (
        "status",
        "gender",
        "created_at",
    )

    search_fields = (
        "account__email",
        "account__first_name",
        "account__last_name",
        "phone",
    )

    ordering = (
        "account__first_name",
        "account__last_name",
    )

    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Cuenta y estado",
            {
                "fields": (
                    "public_id",
                    "account",
                    "status",
                )
            },
        ),
        (
            "Información personal",
            {
                "fields": (
                    "phone",
                    "birth_date",
                    "gender",
                    "address",
                )
            },
        ),
        (
            "Contacto de emergencia",
            {
                "fields": (
                    "emergency_contact_name",
                    "emergency_contact_phone",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def formfield_for_foreignkey(
        self,
        db_field,
        request,
        **kwargs,
    ):
        """
        Limita el selector de cuentas a aquellas
        cuyo rol sea Paciente.
        """

        if db_field.name == "account":
            kwargs["queryset"] = Account.objects.filter(
                role=Account.Role.PATIENT,
            )

        return super().formfield_for_foreignkey(
            db_field,
            request,
            **kwargs,
        )