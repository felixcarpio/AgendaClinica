from django import forms

from apps.appointments.models import Appointment, AvailabilitySlot


class PatientAppointmentConfirmationForm(forms.Form):
    """
    Formulario utilizado por el paciente para confirmar
    la reserva de un horario disponible.
    """

    reason = forms.CharField(
        label="Motivo de consulta",
        max_length=500,
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": (
                    "Describe brevemente el motivo de la consulta."
                ),
            }
        ),
    )

    def clean_reason(self):
        """
        Limpia el motivo y evita guardar textos vacíos
        formados únicamente por espacios.
        """

        reason = self.cleaned_data["reason"].strip()

        if not reason:
            raise forms.ValidationError(
                "Debes indicar el motivo de la consulta."
            )

        return reason
    
    
class PatientAppointmentCancellationForm(forms.Form):
    """
    Formulario utilizado por el paciente para cancelar
    una cita pendiente o confirmada.
    """

    cancelled_reason = forms.CharField(
        label="Motivo de cancelación",
        max_length=500,
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": (
                    "Describe brevemente el motivo de la cancelación."
                ),
            }
        ),
    )

    def clean_cancelled_reason(self):
        """
        Limpia el motivo y evita textos vacíos
        formados únicamente por espacios.
        """

        cancelled_reason = self.cleaned_data[
            "cancelled_reason"
        ].strip()

        if not cancelled_reason:
            raise forms.ValidationError(
                "Debes indicar el motivo de la cancelación."
            )

        return cancelled_reason
    
class PsychologistAppointmentStatusForm(forms.ModelForm):
    """
    Permite al psicólogo actualizar el estado de una cita
    que le pertenece.
    """

    class Meta:
        model = Appointment
        fields = [
            "status",
        ]

        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
        }

        labels = {
            "status": "Estado de la cita",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # El psicólogo únicamente puede gestionar estos estados.
        self.fields["status"].choices = [
            (
                Appointment.Status.PENDING,
                Appointment.Status.PENDING.label,
            ),
            (
                Appointment.Status.CONFIRMED,
                Appointment.Status.CONFIRMED.label,
            ),
            (
                Appointment.Status.COMPLETED,
                Appointment.Status.COMPLETED.label,
            ),
        ]

    def clean_status(self):
        """
        Impide reactivar citas canceladas o completadas.
        """

        new_status = self.cleaned_data["status"]

        if not self.instance.pk:
            return new_status

        current_status = (
            Appointment.objects
            .filter(pk=self.instance.pk)
            .values_list("status", flat=True)
            .first()
        )

        if current_status == Appointment.Status.CANCELLED:
            raise forms.ValidationError(
                "Una cita cancelada no puede cambiar de estado."
            )

        if current_status == Appointment.Status.COMPLETED:
            raise forms.ValidationError(
                "Una cita completada no puede cambiar de estado."
            )

        return new_status
    
class PsychologistAvailabilitySlotForm(forms.ModelForm):
    """
    Permite al psicólogo crear y editar sus propios
    cupos de disponibilidad.

    El psicólogo propietario se asigna desde la vista
    y no puede seleccionarse desde el formulario.
    """

    class Meta:
        model = AvailabilitySlot
        fields = [
            "start_time",
            "end_time",
            "status",
        ]

        widgets = {
            "start_time": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "end_time": forms.DateTimeInput(
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
        }

        labels = {
            "start_time": "Fecha y hora de inicio",
            "end_time": "Fecha y hora de finalización",
            "status": "Estado del cupo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["start_time"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]
        self.fields["end_time"].input_formats = [
            "%Y-%m-%dT%H:%M",
        ]

        # Al crear un cupo, solo puede registrarse como disponible
        # o bloqueado. Un cupo no se crea como reservado.
        if not self.instance.pk:
            self.fields["status"].choices = [
                (
                    AvailabilitySlot.Status.AVAILABLE,
                    AvailabilitySlot.Status.AVAILABLE.label,
                ),
                (
                    AvailabilitySlot.Status.BLOCKED,
                    AvailabilitySlot.Status.BLOCKED.label,
                ),
            ]
            self.initial["status"] = (
                AvailabilitySlot.Status.AVAILABLE
            )

        # Un cupo reservado no debe poder cambiarse manualmente
        # desde este formulario.
        elif (
            self.instance.status
            == AvailabilitySlot.Status.BOOKED
        ):
            self.fields["start_time"].disabled = True
            self.fields["end_time"].disabled = True
            self.fields["status"].disabled = True

        else:
            self.fields["status"].choices = [
                (
                    AvailabilitySlot.Status.AVAILABLE,
                    AvailabilitySlot.Status.AVAILABLE.label,
                ),
                (
                    AvailabilitySlot.Status.BLOCKED,
                    AvailabilitySlot.Status.BLOCKED.label,
                ),
                (
                    AvailabilitySlot.Status.CANCELLED,
                    AvailabilitySlot.Status.CANCELLED.label,
                ),
            ]