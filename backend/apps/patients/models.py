# Create your models here.
from django.db import models
from apps.accounts.models import Account
from django.core.exceptions import ValidationError
import uuid


class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = "MALE", "Masculino"
        FEMALE = "FEMALE", "Femenino"
        OTHER = "OTHER", "Otro"
        PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY", "Prefiero no decirlo"

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="patient_profile"
    )
    phone = models.CharField(max_length=20, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=25,
        choices=Gender.choices,
        blank=True
    )
    address = models.TextField(blank=True)

    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.account and self.account.role != Account.Role.PATIENT:
            raise ValidationError({
                "account": "La cuenta seleccionada debe tener rol de paciente."
            })

    def __str__(self):
        return f"{self.account.first_name} {self.account.last_name}"