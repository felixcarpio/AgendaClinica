from django import forms


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