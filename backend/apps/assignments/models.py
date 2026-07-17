from django.db import models
from django.utils import timezone
from apps.appointments.models import Appointment
from pathlib import Path
from django.core.exceptions import ValidationError
import uuid
from apps.clinical_records.models import SessionNote


class Assignment(models.Model):
    """
    Representa una actividad asignada por el psicólogo al paciente
    como parte del seguimiento de una sesión terapéutica.

    La asignación pertenece a una nota de sesión. El paciente se obtiene
    mediante la relación:

    Assignment -> SessionNote -> ClinicalRecord -> Patient
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        IN_PROGRESS = "IN_PROGRESS", "En progreso"
        COMPLETED = "COMPLETED", "Completada"
        CANCELLED = "CANCELLED", "Cancelada"

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    session_note = models.ForeignKey(
        SessionNote,
        on_delete=models.CASCADE,
        related_name="assignments",
        verbose_name="Nota de sesión",
    )

    title = models.CharField(
        max_length=200,
        verbose_name="Título",
        help_text="Nombre breve de la actividad asignada al paciente.",
    )

    description = models.TextField(
        verbose_name="Descripción",
        help_text=(
            "Instrucciones o detalles que el paciente debe seguir "
            "para realizar la asignación."
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Estado",
    )

    psychologist_comments = models.TextField(
        blank=True,
        verbose_name="Comentarios del psicólogo",
        help_text=(
            "Indicaciones u observaciones adicionales visibles para el paciente."
        ),
    )

    patient_response = models.TextField(
        blank=True,
        verbose_name="Respuesta del paciente",
        help_text=(
            "Contenido escrito por el paciente como respuesta a la asignación."
        ),
    )

    is_visible = models.BooleanField(
        default=True,
        verbose_name="Visible para el paciente",
        help_text=(
            "Indica si la asignación puede mostrarse en el portal del paciente."
        ),
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de finalización",
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
        verbose_name = "Asignación"
        verbose_name_plural = "Asignaciones"
        ordering = ["-created_at"]

    def __str__(self):
        patient = self.session_note.clinical_record.patient
        return f"{self.title} - {patient}"

    def clean(self):
        """
        Valida que la asignación esté asociada a una nota de sesión
        cuya cita se encuentre completada.
        """

        super().clean()

        # Si todavía no se ha seleccionado una nota de sesión,
        # dejamos que Django gestione el error de campo obligatorio.
        if not self.session_note_id:
            return

        appointment = self.session_note.appointment

        if appointment.status != Appointment.Status.COMPLETED:
            raise ValidationError(
                {
                    "session_note": (
                        "Solo es posible crear asignaciones para notas "
                        "de sesiones asociadas a citas completadas."
                    )
                }
            )
            
    def save(self, *args, **kwargs):
        """
        Sincroniza automáticamente la visibilidad y la fecha
        de finalización antes de guardar la asignación.
        """

        # Las asignaciones canceladas se ocultan automáticamente.
        # Si el psicólogo las reactiva, vuelven a ser visibles.
        self.is_visible = self.status != self.Status.CANCELLED

        # Al completarse, se registra la fecha de finalización.
        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()

        # Si deja de estar completada, se elimina la fecha anterior.
        if self.status != self.Status.COMPLETED:
            self.completed_at = None

        self.full_clean()
        super().save(*args, **kwargs)
        
        
class AssignmentAttachment(models.Model):
    """
    Representa un archivo adjunto relacionado con una asignación.

    Los archivos pueden ser proporcionados por el psicólogo como material
    de apoyo o enviados por el paciente como parte de su respuesta.
    """

    class UploadedBy(models.TextChoices):
        PSYCHOLOGIST = "PSYCHOLOGIST", "Psicólogo"
        PATIENT = "PATIENT", "Paciente"

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Asignación",
    )

    file = models.FileField(
        upload_to="assignments/attachments/%Y/%m/",
        verbose_name="Archivo",
    )

    uploaded_by = models.CharField(
        max_length=20,
        choices=UploadedBy.choices,
        verbose_name="Subido por",
    )

    original_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nombre original",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de carga",
    )

    class Meta:
        verbose_name = "Archivo adjunto"
        verbose_name_plural = "Archivos adjuntos"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_name or self.file.name} - {self.assignment}"

    def save(self, *args, **kwargs):
        """
        Conserva automáticamente el nombre original del archivo.
        """

        if self.file and not self.original_name:
            self.original_name = Path(self.file.name).name

        self.full_clean()
        super().save(*args, **kwargs)