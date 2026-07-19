from django import forms
from django.db.models import Q
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.patients.models import Patient

from .models import ClinicalRecord, SessionNote


class ClinicalRecordAdminForm(forms.ModelForm):
    """
    Formulario personalizado para crear y editar expedientes clínicos
    desde el administrador de Django.
    """

    class Meta:
        model = ClinicalRecord
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Al crear un expediente, solo se muestran pacientes
        # que todavía no tienen un expediente clínico asociado.
        queryset = Patient.objects.filter(
            clinical_record__isnull=True,
        )

        # Al editar un expediente existente, también se incluye
        # al paciente actualmente relacionado con el expediente.
        if self.instance and self.instance.pk:
            queryset = Patient.objects.filter(
                Q(clinical_record__isnull=True)
                | Q(pk=self.instance.patient_id)
            )

        self.fields["patient"].queryset = queryset.order_by(
            "account__first_name",
            "account__last_name",
        )


class SessionNoteAdminForm(forms.ModelForm):
    """
    Formulario personalizado para crear y editar notas de sesión
    desde el administrador de Django.
    """

    class Meta:
        model = SessionNote
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Solo se muestran citas completadas, cuya fecha y hora
        # de finalización ya hayan ocurrido y que todavía no tengan
        # una nota de sesión asociada.
        appointments = (
            Appointment.objects
            .filter(
                status=Appointment.Status.COMPLETED,
                availability_slot__end_time__lte=timezone.now(),
                session_note__isnull=True,
            )
            .select_related(
                "patient",
                "patient__account",
                "psychologist",
                "psychologist__account",
                "availability_slot",
            )
            .order_by(
                "-availability_slot__start_time",
            )
        )

        # Al editar una nota existente, también se conserva
        # su cita actual dentro del selector.
        if self.instance and self.instance.pk:
            appointments = (
                Appointment.objects
                .filter(
                    Q(
                        status=Appointment.Status.COMPLETED,
                        availability_slot__end_time__lte=timezone.now(),
                        session_note__isnull=True,
                    )
                    | Q(pk=self.instance.appointment_id)
                )
                .select_related(
                    "patient",
                    "patient__account",
                    "psychologist",
                    "psychologist__account",
                    "availability_slot",
                )
                .distinct()
                .order_by(
                    "-availability_slot__start_time",
                )
            )

        self.fields["appointment"].queryset = appointments


class SessionNoteForm(forms.ModelForm):
    """
    Formulario utilizado por el psicólogo para registrar
    o actualizar la nota clínica de una sesión completada.

    El expediente clínico y la cita se asignan desde la vista
    para evitar que puedan modificarse manualmente.
    """

    class Meta:
        model = SessionNote
        fields = [
            "session_summary",
            "observations",
            "interventions",
            "homework",
            "next_session_plan",
        ]

        widgets = {
            "session_summary": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Describe los principales temas abordados "
                        "durante la sesión."
                    ),
                }
            ),
            "observations": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Registra las observaciones clínicas relevantes."
                    ),
                }
            ),
            "interventions": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Describe las técnicas o intervenciones aplicadas."
                    ),
                }
            ),
            "homework": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Registra las actividades acordadas con el paciente."
                    ),
                }
            ),
            "next_session_plan": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Describe los temas u objetivos para la próxima sesión."
                    ),
                }
            ),
        }

    def clean_session_summary(self):
        """
        Evita guardar un resumen vacío o compuesto únicamente
        por espacios.
        """

        session_summary = self.cleaned_data["session_summary"].strip()

        if not session_summary:
            raise forms.ValidationError(
                "Debes ingresar un resumen de la sesión."
            )

        return session_summary
    
class ClinicalRecordForm(forms.ModelForm):
    """
    Formulario utilizado por el psicólogo para actualizar
    la información general del expediente clínico.

    El paciente no se incluye porque el expediente ya se encuentra
    vinculado desde la vista.
    """

    class Meta:
        model = ClinicalRecord
        fields = [
            "chief_complaint",
            "personal_history",
            "family_history",
            "medical_history",
            "current_medication",
            "initial_assessment",
            "therapeutic_objectives",
            "general_observations",
        ]

        widgets = {
            "chief_complaint": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Describe el motivo principal por el que el paciente "
                        "inicia el proceso terapéutico."
                    ),
                }
            ),
            "personal_history": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Registra antecedentes personales relevantes."
                    ),
                }
            ),
            "family_history": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Registra antecedentes familiares relevantes."
                    ),
                }
            ),
            "medical_history": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Registra antecedentes médicos relevantes."
                    ),
                }
            ),
            "current_medication": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": (
                        "Registra la medicación actual del paciente."
                    ),
                }
            ),
            "initial_assessment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Registra las observaciones e impresiones "
                        "de la evaluación inicial."
                    ),
                }
            ),
            "therapeutic_objectives": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Describe los objetivos principales del proceso "
                        "terapéutico."
                    ),
                }
            ),
            "general_observations": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Registra cualquier información adicional relevante."
                    ),
                }
            ),
        }