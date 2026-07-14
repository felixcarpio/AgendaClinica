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
            clinical_record__isnull=True
        )

        # Al editar un expediente existente, también se incluye
        # al paciente actualmente relacionado con el expediente.
        if self.instance and self.instance.pk:
            queryset = Patient.objects.filter(
                Q(clinical_record__isnull=True)
                | Q(pk=self.instance.patient_id)
            )

        self.fields["patient"].queryset = queryset


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

        # Solo se muestran citas completadas cuya fecha y hora
        # de finalización ya hayan ocurrido.
        appointments = Appointment.objects.filter(
            status=Appointment.Status.COMPLETED,
            availability_slot__end_time__lte=timezone.now(),
        ).select_related(
            "patient",
            "psychologist",
            "availability_slot",
        ).order_by(
            "-availability_slot__start_time"
        )

        # Al editar una nota existente, conservamos su cita actual
        # dentro del selector.
        if self.instance and self.instance.pk:
            appointments = Appointment.objects.filter(
                Q(
                    status=Appointment.Status.COMPLETED,
                    availability_slot__end_time__lte=timezone.now(),
                )
                | Q(pk=self.instance.appointment_id)
            ).select_related(
                "patient",
                "psychologist",
                "availability_slot",
            ).order_by(
                "-availability_slot__start_time"
            )

        self.fields["appointment"].queryset = appointments