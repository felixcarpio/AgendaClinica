import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.psychologists.models import Psychologist
from apps.accounts.models import Account


class Patient(models.Model):
    """
    Representa el perfil clínico y administrativo de un paciente.

    Cada paciente está relacionado con una cuenta cuyo rol
    debe ser PATIENT.
    """

    class Gender(models.TextChoices):
        MALE = "MALE", "Masculino"
        FEMALE = "FEMALE", "Femenino"
        OTHER = "OTHER", "Otro"
        PREFER_NOT_TO_SAY = (
            "PREFER_NOT_TO_SAY",
            "Prefiero no decirlo",
        )

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        INACTIVE = "INACTIVE", "Inactivo"
        DISCHARGED = "DISCHARGED", "Dado de alta"

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
    )

    birth_date = models.DateField(
        null=True,
        blank=True,
    )

    gender = models.CharField(
        max_length=25,
        choices=Gender.choices,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Estado",
        help_text=(
            "Indica si el paciente se encuentra actualmente "
            "en atención o seguimiento."
        ),
    )

    address = models.TextField(
        blank=True,
    )

    emergency_contact_name = models.CharField(
        max_length=150,
        blank=True,
    )

    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = [
            "account__first_name",
            "account__last_name",
        ]

    def clean(self):
        """
        Verifica que la cuenta relacionada tenga rol de paciente.
        """

        super().clean()

        if (
            self.account
            and self.account.role != Account.Role.PATIENT
        ):
            raise ValidationError(
                {
                    "account": (
                        "La cuenta seleccionada debe tener "
                        "rol de paciente."
                    )
                }
            )

    def __str__(self):
        return (
            f"{self.account.first_name} "
            f"{self.account.last_name}"
        )
        
class PatientPsychologistRelationship(models.Model):
    """
    Representa la relación de atención entre un paciente
    y un psicólogo.

    Permite que un paciente exista en el listado del psicólogo
    aunque todavía no tenga citas registradas.

    También conserva relaciones anteriores cuando el paciente
    cambia de profesional, interrumpe su proceso o recibe el alta.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Activo"
        INACTIVE = "INACTIVE", "Inactivo"
        DISCHARGED = "DISCHARGED", "Dado de alta"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="psychologist_relationships",
        verbose_name="Paciente",
    )

    psychologist = models.ForeignKey(
        Psychologist,
        on_delete=models.PROTECT,
        related_name="patient_relationships",
        verbose_name="Psicólogo",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Estado de la relación",
    )

    started_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de inicio",
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de finalización",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Relación paciente-psicólogo"
        verbose_name_plural = "Relaciones paciente-psicólogo"
        ordering = (
            "-started_at",
        )
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "patient",
                    "psychologist",
                ),
                condition=Q(status="ACTIVE"),
                name="unique_active_patient_psychologist_relationship",
            ),
        ]

    def clean(self):
        """
        Valida la coherencia entre el estado y la fecha de finalización.
        """

        super().clean()

        if self.status == self.Status.ACTIVE:
            self.ended_at = None

        elif self.ended_at is None:
            self.ended_at = timezone.now()

    def save(self, *args, **kwargs):
        """
        Ejecuta las validaciones antes de guardar la relación.
        """

        self.full_clean()

        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.patient} - "
            f"{self.psychologist} - "
            f"{self.get_status_display()}"
        )