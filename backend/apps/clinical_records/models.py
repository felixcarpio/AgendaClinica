from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.appointments.models import Appointment
from apps.patients.models import Patient


class ClinicalRecord(models.Model):
    """
    Representa el expediente clínico principal de un paciente.

    Cada paciente tendrá un único expediente clínico, dentro del cual
    se almacenarán las notas de las sesiones y otra información
    relacionada con su proceso terapéutico.
    """

    patient = models.OneToOneField(
        Patient,
        on_delete=models.CASCADE,
        related_name="clinical_record",
        verbose_name="Paciente",
    )
    
    chief_complaint = models.TextField(
        blank=True,
        verbose_name="Motivo de consulta",
        help_text=(
            "Describe la razón principal por la que el paciente inicia "
            "el proceso terapéutico."
        ),
    )
    
    personal_history = models.TextField(
        blank=True,
        verbose_name="Antecedentes personales",
        help_text=(
            "Registra acontecimientos, experiencias o situaciones personales "
            "relevantes para el proceso terapéutico."
        ),
    )

    family_history = models.TextField(
        blank=True,
        verbose_name="Antecedentes familiares",
        help_text=(
            "Registra información relevante sobre la dinámica familiar "
            "y antecedentes psicológicos o médicos en la familia."
        ),
    )

    medical_history = models.TextField(
        blank=True,
        verbose_name="Antecedentes médicos",
        help_text=(
            "Registra enfermedades, tratamientos, cirugías u otra información "
            "médica relevante del paciente."
        ),
    )

    current_medication = models.TextField(
        blank=True,
        verbose_name="Medicación actual",
        help_text=(
            "Registra los medicamentos que el paciente utiliza actualmente, "
            "incluyendo dosis o frecuencia cuando sea relevante."
        ),
    )
    
    initial_assessment = models.TextField(
        blank=True,
        verbose_name="Evaluación inicial",
        help_text=(
            "Registra las observaciones, impresiones clínicas e "
            "hipótesis obtenidas durante la evaluación inicial del paciente."
        ),
    )
    
    therapeutic_objectives = models.TextField(
        blank=True,
        verbose_name="Objetivos terapéuticos",
        help_text=(
            "Registra los objetivos principales que se esperan trabajar "
            "durante el proceso terapéutico."
        ),
    )

    general_observations = models.TextField(
        blank=True,
        verbose_name="Observaciones generales",
        help_text=(
            "Registra información adicional relevante sobre el expediente "
            "o el proceso terapéutico del paciente."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización",
    )

    class Meta:
        verbose_name = "Expediente clínico"
        verbose_name_plural = "Expedientes clínicos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Expediente clínico de {self.patient}"


class SessionNote(models.Model):
    """
    Representa una nota clínica elaborada por el psicólogo después
    de atender una sesión con el paciente.

    Cada nota pertenece a un expediente clínico y a una cita
    específica. Una misma cita puede tener varias notas asociadas.
    """

    clinical_record = models.ForeignKey(
        ClinicalRecord,
        on_delete=models.CASCADE,
        related_name="session_notes",
        verbose_name="Expediente clínico",
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.PROTECT,
        related_name="session_notes",
        verbose_name="Cita",
    )

    session_summary = models.TextField(
        verbose_name="Resumen de la sesión",
        help_text="Descripción general de los temas abordados durante la sesión.",
    )

    observations = models.TextField(
        blank=True,
        verbose_name="Observaciones",
        help_text="Observaciones clínicas relevantes identificadas durante la sesión.",
    )

    interventions = models.TextField(
        blank=True,
        verbose_name="Técnicas o intervenciones",
        help_text="Técnicas, ejercicios o intervenciones aplicadas durante la sesión.",
    )

    homework = models.TextField(
        blank=True,
        verbose_name="Tareas asignadas",
        help_text="Actividades o tareas acordadas con el paciente.",
    )

    next_session_plan = models.TextField(
        blank=True,
        verbose_name="Plan para la siguiente sesión",
        help_text="Temas u objetivos que se trabajarán en la próxima sesión.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización",
    )

    class Meta:
        verbose_name = "Nota de sesión"
        verbose_name_plural = "Notas de sesión"
        ordering = ["-appointment__availability_slot__start_time"]

    def __str__(self):
        return f"Nota de sesión - {self.appointment}"
    
    def clean(self):
        """
        Valida las reglas de negocio para registrar una nota de sesión.

        - La cita debe pertenecer al mismo paciente del expediente.
        - La cita debe haber finalizado.
        - La cita debe encontrarse en estado completado.
        """

        super().clean()

        # Si todavía no se ha seleccionado el expediente o la cita,
        # dejamos que Django gestione los errores de campos obligatorios.
        if not self.clinical_record_id or not self.appointment_id:
            return

        appointment_errors = []

        # La cita debe pertenecer al mismo paciente del expediente.
        if self.clinical_record.patient_id != self.appointment.patient_id:
            appointment_errors.append(
                "La cita seleccionada no pertenece al paciente del expediente clínico."
            )

        # La cita debe haber finalizado.
        if self.appointment.availability_slot.end_time > timezone.now():
            appointment_errors.append(
                "No es posible registrar una nota hasta que la cita haya finalizado."
            )

        # La cita debe estar completada.
        if self.appointment.status != Appointment.Status.COMPLETED:
            appointment_errors.append(
                "Solo es posible registrar notas para citas completadas."
            )

        if appointment_errors:
            raise ValidationError(
                {
                    "appointment": appointment_errors,
                }
            )
            
    def save(self, *args, **kwargs):
        """
        Ejecuta las validaciones antes de guardar la nota de sesión.
        """
        self.full_clean()
        super().save(*args, **kwargs)