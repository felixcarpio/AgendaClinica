from django import forms
from django.db.models import Q

from apps.appointments.models import Appointment
from apps.clinical_records.models import SessionNote

from .models import Assignment


class AssignmentPsychologistForm(forms.ModelForm):
    """
    Formulario utilizado por el psicólogo para crear y administrar
    asignaciones terapéuticas.

    El psicólogo puede modificar las instrucciones, comentarios y estado,
    pero no la respuesta escrita por el paciente.
    """

    class Meta:
        model = Assignment
        fields = (
            "session_note",
            "title",
            "description",
            "status",
            "psychologist_comments",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Solo se muestran notas asociadas a citas completadas.
        notes = SessionNote.objects.filter(
            appointment__status=Appointment.Status.COMPLETED
        ).select_related(
            "clinical_record__patient",
            "appointment__availability_slot",
        ).order_by(
            "-appointment__availability_slot__start_time"
        )

        # Al editar una asignación, también se conserva
        # la nota actualmente relacionada.
        if self.instance and self.instance.pk:
            notes = SessionNote.objects.filter(
                Q(
                    appointment__status=Appointment.Status.COMPLETED
                )
                | Q(pk=self.instance.session_note_id)
            ).select_related(
                "clinical_record__patient",
                "appointment__availability_slot",
            ).order_by(
                "-appointment__availability_slot__start_time"
            )

        self.fields["session_note"].queryset = notes


class AssignmentPatientForm(forms.ModelForm):
    """
    Formulario utilizado por el paciente para responder y actualizar
    el progreso de una asignación.

    El paciente no puede modificar las instrucciones, cancelarla
    ni reabrir una asignación completada.
    """

    class Meta:
        model = Assignment
        fields = (
            "patient_response",
            "status",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_status = self.instance.status

        # Las opciones disponibles dependen del estado actual.
        allowed_choices = {
            Assignment.Status.PENDING: (
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
            ),
            Assignment.Status.IN_PROGRESS: (
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
            ),
            Assignment.Status.COMPLETED: (
                Assignment.Status.COMPLETED,
            ),
            Assignment.Status.CANCELLED: (
                Assignment.Status.CANCELLED,
            ),
        }

        allowed_values = allowed_choices.get(current_status, ())

        self.fields["status"].choices = [
            choice
            for choice in Assignment.Status.choices
            if choice[0] in allowed_values
        ]

    def clean_status(self):
        """
        Valida que el paciente únicamente realice transiciones
        de estado permitidas.
        """

        new_status = self.cleaned_data["status"]
        current_status = self.instance.status

        allowed_transitions = {
            Assignment.Status.PENDING: {
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
            },
            Assignment.Status.IN_PROGRESS: {
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
            },
            Assignment.Status.COMPLETED: {
                Assignment.Status.COMPLETED,
            },
            Assignment.Status.CANCELLED: {
                Assignment.Status.CANCELLED,
            },
        }

        if new_status not in allowed_transitions.get(current_status, set()):
            raise forms.ValidationError(
                "No tienes permiso para realizar este cambio de estado."
            )

        return new_status