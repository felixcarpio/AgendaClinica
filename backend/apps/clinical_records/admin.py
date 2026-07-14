from django.contrib import admin
from .models import ClinicalRecord, SessionNote
from .forms import ClinicalRecordAdminForm, SessionNoteAdminForm


@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    """
    Configuración del administrador para los expedientes clínicos.
    """

    form = ClinicalRecordAdminForm

    list_display = (
        "id",
        "patient",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "patient__account__first_name",
        "patient__account__last_name",
        "patient__account__email",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Información general",
            {
                "fields": (
                    "patient",
                    "chief_complaint",
                )
            },
        ),
        (
            "Antecedentes",
            {
                "fields": (
                    "personal_history",
                    "family_history",
                    "medical_history",
                    "current_medication",
                )
            },
        ),
        (
            "Evaluación inicial",
            {
                "fields": (
                    "initial_assessment",
                )
            },
        ),
        (
            "Plan terapéutico",
            {
                "fields": (
                    "therapeutic_objectives",
                )
            },
        ),
        (
            "Observaciones",
            {
                "fields": (
                    "general_observations",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": (
                    "collapse",
                ),
            },
        ),
    )
    
    list_select_related = (
        "patient",
    )
    
@admin.register(SessionNote)
class SessionNoteAdmin(admin.ModelAdmin):
    """
    Configuración del administrador para las notas de sesión.
    """

    form = SessionNoteAdminForm

    list_display = (
        "id",
        "clinical_record",
        "appointment",
        "created_at",
    )

    search_fields = (
        "clinical_record__patient__account__first_name",
        "clinical_record__patient__account__last_name",
        "appointment__patient__account__first_name",
        "appointment__patient__account__last_name",
    )

    list_filter = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    
    list_select_related = (
        "clinical_record__patient",
        "appointment__patient",
        "appointment__psychologist",
        "appointment__availability_slot",
    )