from django.contrib import admin
from .models import Assignment, AssignmentAttachment
from .forms import AssignmentPsychologistForm

class AssignmentAttachmentInline(admin.TabularInline):
    """
    Permite administrar los archivos adjuntos directamente
    desde el formulario de una asignación.
    """

    model = AssignmentAttachment
    extra = 1

    fields = (
        "file",
        "uploaded_by",
        "original_name",
        "created_at",
    )

    readonly_fields = (
        "original_name",
        "created_at",
    )

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    """
    Configuración del administrador para las asignaciones
    terapéuticas de los pacientes.
    """

    form = AssignmentPsychologistForm

    list_display = (
        "id",
        "title",
        "get_patient",
        "status",
        "is_visible",
        "completed_at",
        "created_at",
    )
    
    inlines = (
        AssignmentAttachmentInline,
    )

    list_filter = (
        "status",
        "is_visible",
        "created_at",
    )

    search_fields = (
        "title",
        "description",
        "session_note__clinical_record__patient__account__first_name",
        "session_note__clinical_record__patient__account__last_name",
        "session_note__clinical_record__patient__account__email",
    )

    ordering = (
        "-created_at",
    )

    readonly_fields = (
        "patient_response",
        "is_visible",
        "completed_at",
        "created_at",
        "updated_at",
    )

    list_select_related = (
        "session_note__clinical_record__patient",
    )

    fieldsets = (
        (
            "Asignación",
            {
                "fields": (
                    "session_note",
                    "title",
                    "description",
                    "status",
                )
            },
        ),
        (
            "Seguimiento",
            {
                "fields": (
                    "psychologist_comments",
                    "patient_response",
                )
            },
        ),
        (
            "Estado interno",
            {
                "fields": (
                    "is_visible",
                    "completed_at",
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
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Paciente")
    def get_patient(self, obj):
        """
        Obtiene el paciente relacionado a través de la nota de sesión.
        """
        return obj.session_note.clinical_record.patient