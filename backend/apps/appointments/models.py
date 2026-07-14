from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.patients.models import Patient
from apps.psychologists.models import Psychologist


class AvailabilitySlot(models.Model):
    """
    Representa un cupo de disponibilidad creado por un psicólogo.

    Un cupo define un rango de fecha y hora que posteriormente puede
    utilizarse para crear una cita.
    """

    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponible"
        BOOKED = "BOOKED", "Reservado"
        BLOCKED = "BLOCKED", "Bloqueado"
        CANCELLED = "CANCELLED", "Cancelado"

    # Psicólogo propietario del cupo.
    psychologist = models.ForeignKey(
        Psychologist,
        on_delete=models.CASCADE,
        related_name="availability_slots",
    )

    # Fecha y hora de inicio del cupo.
    start_time = models.DateTimeField()

    # Fecha y hora de finalización del cupo.
    end_time = models.DateTimeField()

    # Estado actual del cupo.
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )

    # Fechas de auditoría.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Los cupos se mostrarán ordenados por su fecha de inicio.
        ordering = ["start_time"]

    def clean(self):
        """
        Ejecuta las validaciones de negocio antes de guardar el cupo.
        """

        # La fecha final siempre debe ser posterior a la fecha inicial.
        if self.end_time <= self.start_time:
            raise ValidationError({
                "end_time": (
                    "La fecha u hora final debe ser posterior "
                    "a la fecha u hora inicial."
                )
            })

        # Al crear un nuevo cupo, no se permiten fechas u horas pasadas.
        #
        # La condición `not self.pk` evita que un cupo histórico genere
        # errores si posteriormente se necesita consultar o modificar.
        if not self.pk and self.start_time < timezone.now():
            raise ValidationError({
                "start_time": (
                    "No se puede crear un cupo en una fecha u hora pasada."
                )
            })

        # Busca otros cupos del mismo psicólogo que se crucen
        # con el rango de tiempo seleccionado.
        overlapping_slots = AvailabilitySlot.objects.filter(
            psychologist=self.psychologist,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        )

        # Cuando se edita un cupo, se excluye a sí mismo de la búsqueda.
        if self.pk:
            overlapping_slots = overlapping_slots.exclude(pk=self.pk)

        # No se permite que un psicólogo tenga dos cupos solapados.
        if overlapping_slots.exists():
            raise ValidationError({
                "start_time": (
                    "Este psicólogo ya tiene un cupo que se cruza "
                    "con el horario seleccionado."
                )
            })

    def __str__(self):
        local_start = timezone.localtime(self.start_time)
        local_end = timezone.localtime(self.end_time)

        return (
            f"{self.psychologist} - "
            f"{local_start.strftime('%d/%m/%Y %I:%M %p')} "
            f"a {local_end.strftime('%I:%M %p')}"
        )


class Appointment(models.Model):
    """
    Representa una cita entre un paciente y un psicólogo.

    La cita está asociada a un único cupo de disponibilidad.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        CONFIRMED = "CONFIRMED", "Confirmada"
        CANCELLED = "CANCELLED", "Cancelada"
        COMPLETED = "COMPLETED", "Completada"

    class AppointmentType(models.TextChoices):
        IN_PERSON = "IN_PERSON", "Presencial"
        VIRTUAL = "VIRTUAL", "Virtual"

    # Paciente que recibirá la atención.
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="appointments",
    )

    # Psicólogo encargado de la atención.
    psychologist = models.ForeignKey(
        Psychologist,
        on_delete=models.CASCADE,
        related_name="appointments",
    )

    # Cada cupo solamente puede utilizarse para una cita.
    #
    # PROTECT evita eliminar un cupo que ya esté asociado a una cita.
    availability_slot = models.OneToOneField(
        AvailabilitySlot,
        on_delete=models.PROTECT,
        related_name="appointment",
    )

    # Estado actual de la cita.
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Motivo inicial por el que el paciente solicita la cita.
    reason = models.TextField(blank=True)

    # Indica si la atención será presencial o virtual.
    appointment_type = models.CharField(
        max_length=20,
        choices=AppointmentType.choices,
        default=AppointmentType.IN_PERSON,
    )

    # Observaciones administrativas que no forman parte
    # del expediente clínico del paciente.
    administrative_notes = models.TextField(blank=True)

    # Motivo por el cual se canceló la cita.
    cancelled_reason = models.TextField(blank=True)

    # Fechas de auditoría.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Las citas se mostrarán ordenadas por la fecha del cupo.
        ordering = ["availability_slot__start_time"]

    def clean(self):
        """
        Ejecuta las reglas de negocio de la cita antes de guardarla.
        """

        # El cupo seleccionado debe pertenecer al mismo psicólogo
        # que fue asignado a la cita.
        if self.availability_slot.psychologist != self.psychologist:
            raise ValidationError({
                "availability_slot": (
                    "El cupo seleccionado no pertenece "
                    "al psicólogo indicado."
                )
            })

        # Si el cupo no está disponible, solo se permite conservarlo
        # cuando pertenece a la misma cita que se está editando.
        if self.availability_slot.status != AvailabilitySlot.Status.AVAILABLE:
            # Una cita nueva solamente puede utilizar un cupo disponible.
            if not self.pk:
                raise ValidationError({
                    "availability_slot": (
                        "Solo se pueden reservar cupos "
                        "con estado Disponible."
                    )
                })

            # Obtiene la versión actual de la cita almacenada
            # para comprobar cuál era su cupo original.
            current_appointment = Appointment.objects.get(pk=self.pk)

            # Si se intenta cambiar a otro cupo no disponible,
            # la operación debe rechazarse.
            if (
                current_appointment.availability_slot
                != self.availability_slot
            ):
                raise ValidationError({
                    "availability_slot": (
                        "Solo se pueden reservar cupos "
                        "con estado Disponible."
                    )
                })

        # Una cita cancelada debe tener un motivo de cancelación.
        if (
            self.status == self.Status.CANCELLED
            and not self.cancelled_reason.strip()
        ):
            raise ValidationError({
                "cancelled_reason": (
                    "Debes indicar el motivo de cancelación."
                )
            })

        # El motivo de cancelación no debe utilizarse
        # en citas que continúan activas o que fueron completadas.
        if (
            self.status != self.Status.CANCELLED
            and self.cancelled_reason.strip()
        ):
            raise ValidationError({
                "cancelled_reason": (
                    "El motivo de cancelación solo debe completarse "
                    "para citas canceladas."
                )
            })

        # Las citas pendientes y confirmadas se consideran activas.
        active_statuses = [
            self.Status.PENDING,
            self.Status.CONFIRMED,
        ]

        # Las validaciones de cruces solo aplican a citas activas.
        if self.status in active_statuses:
            # Busca citas activas del paciente que se crucen
            # con el horario seleccionado.
            overlapping_appointments = Appointment.objects.filter(
                patient=self.patient,
                status__in=active_statuses,
                availability_slot__start_time__lt=(
                    self.availability_slot.end_time
                ),
                availability_slot__end_time__gt=(
                    self.availability_slot.start_time
                ),
            )

            # Al editar una cita, se excluye la cita actual.
            if self.pk:
                overlapping_appointments = overlapping_appointments.exclude(
                    pk=self.pk
                )

            # El paciente no puede tener dos citas activas al mismo tiempo.
            if overlapping_appointments.exists():
                raise ValidationError({
                    "availability_slot": (
                        "El paciente ya tiene otra cita activa "
                        "que se cruza con este horario."
                    )
                })

            # Busca citas activas del psicólogo que se crucen
            # con el horario seleccionado.
            overlapping_psychologist_appointments = Appointment.objects.filter(
                psychologist=self.psychologist,
                status__in=active_statuses,
                availability_slot__start_time__lt=self.availability_slot.end_time,
                availability_slot__end_time__gt=self.availability_slot.start_time,
            )

            # Al editar una cita, se excluye la cita actual.
            if self.pk:
                overlapping_psychologist_appointments = (
                    overlapping_psychologist_appointments.exclude(pk=self.pk)
                )

            # El psicólogo no puede atender dos citas activas al mismo tiempo.
            if overlapping_psychologist_appointments.exists():
                raise ValidationError({
                    "availability_slot": (
                        "El psicólogo ya tiene otra cita activa "
                        "que se cruza con este horario."
                    )
                })

    def save(self, *args, **kwargs):
        """
        Guarda la cita y sincroniza el estado de sus cupos.

        - Una cita activa reserva su cupo.
        - Una cita cancelada libera su cupo.
        - Si se cambia el cupo, se libera el anterior.
        """

        old_slot = None

        # Si la cita ya existe, se obtiene el cupo anterior
        # antes de guardar cualquier modificación.
        if self.pk:
            old_appointment = Appointment.objects.get(pk=self.pk)
            old_slot = old_appointment.availability_slot

        # Ejecuta todas las validaciones del modelo.
        self.full_clean()

        # Guarda la cita.
        super().save(*args, **kwargs)

        # Si la cita cambió de cupo, se libera el cupo anterior.
        if old_slot and old_slot != self.availability_slot:
            old_slot.status = AvailabilitySlot.Status.AVAILABLE
            old_slot.save(update_fields=["status", "updated_at"])

        # Una cita cancelada deja nuevamente disponible su cupo.
        if self.status == self.Status.CANCELLED:
            self.availability_slot.status = (
                AvailabilitySlot.Status.AVAILABLE
            )
        else:
            # Las citas pendientes, confirmadas o completadas
            # mantienen reservado el cupo.
            self.availability_slot.status = (
                AvailabilitySlot.Status.BOOKED
            )

        # Guarda únicamente los campos que cambiaron en el cupo.
        self.availability_slot.save(
            update_fields=["status", "updated_at"]
        )

    @property
    def duration(self):
        """
        Devuelve la duración de la cita como un objeto timedelta.
        """
        return (
            self.availability_slot.end_time
            - self.availability_slot.start_time
        )


    @property
    def is_virtual(self):
        """
        Indica si la cita se realizará de forma virtual.
        """
        return self.appointment_type == self.AppointmentType.VIRTUAL


    @property
    def is_active(self):
        """
        Indica si la cita continúa activa.
        """
        return self.status in [
            self.Status.PENDING,
            self.Status.CONFIRMED,
        ]


    @property
    def is_finished(self):
        """
        Indica si la cita ya fue completada.
        """
        return self.status == self.Status.COMPLETED

    def __str__(self):
        """
        Devuelve la cita con sus horas de inicio y finalización
        convertidas a la zona horaria local.
        """

        local_start_time = timezone.localtime(
            self.availability_slot.start_time
        )
        local_end_time = timezone.localtime(
            self.availability_slot.end_time
        )

        return (
            f"{self.patient} con {self.psychologist} - "
            f"{local_start_time.strftime('%d/%m/%Y')} "
            f"{local_start_time.strftime('%I:%M %p')} a "
            f"{local_end_time.strftime('%I:%M %p')}"
        )