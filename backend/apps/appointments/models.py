from django.db import models

from apps.psychologists.models import Psychologist
from apps.patients.models import Patient
from django.core.exceptions import ValidationError
from django.utils import timezone

class AvailabilitySlot(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponible"
        BOOKED = "BOOKED", "Reservado"
        BLOCKED = "BLOCKED", "Bloqueado"
        CANCELLED = "CANCELLED", "Cancelado"

    psychologist = models.ForeignKey(
        Psychologist,
        on_delete=models.CASCADE,
        related_name="availability_slots"
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_time"]

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError({
                "end_time": "La fecha u hora final debe ser posterior a la fecha inicial."
            })
        
        if self.start_time < timezone.now():
            raise ValidationError({
            "start_time": "No se puede crear un cupo en una fecha/hora pasada."
            })

        overlapping_slots = AvailabilitySlot.objects.filter(
        psychologist=self.psychologist,
        start_time__lt=self.end_time,
        end_time__gt=self.start_time
        )

        if self.pk:
            overlapping_slots = overlapping_slots.exclude(pk=self.pk)

        if overlapping_slots.exists():
            raise ValidationError(
                "Este psicólogo ya tiene un cupo que se cruza con ese horario."
            )

    def __str__(self):
        psychologist_name = (
            f"{self.psychologist.account.first_name} "
            f"{self.psychologist.account.last_name}"
        )
        return f"{psychologist_name} | {self.start_time} - {self.end_time}"
    



### MODELO PARA CITAS   
class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pendiente"
        CONFIRMED = "CONFIRMED", "Confirmada"
        CANCELLED = "CANCELLED", "Cancelada"
        COMPLETED = "COMPLETED", "Completada"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    psychologist = models.ForeignKey(
        Psychologist,
        on_delete=models.CASCADE,
        related_name="appointments"
    )

    availability_slot = models.OneToOneField(
        AvailabilitySlot,
        on_delete=models.PROTECT,
        related_name="appointment"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["availability_slot__start_time"]

    def clean(self):
        if self.availability_slot.psychologist != self.psychologist:
            raise ValidationError({
                "availability_slot": "El availability slot seleccionado no pertenece al psicólogo indicado."
            })

        if self.availability_slot.status != AvailabilitySlot.Status.AVAILABLE:
            raise ValidationError({
                "availability_slot": "Solo se pueden reservar availability slots con estado Disponible."
            })


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        if self.availability_slot.status == AvailabilitySlot.Status.AVAILABLE:
            self.availability_slot.status = AvailabilitySlot.Status.BOOKED
            self.availability_slot.save()


    def __str__(self):
        return f"{self.patient} con {self.psychologist} - {self.availability_slot.start_time}"