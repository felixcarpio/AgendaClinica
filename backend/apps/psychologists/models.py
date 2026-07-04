from django.db import models
from apps.accounts.models import Account
from django.core.exceptions import ValidationError


class Psychologist(models.Model):
    class AttentionMode(models.TextChoices):
        IN_PERSON = "IN_PERSON", "Presencial"
        ONLINE = "ONLINE", "En línea"
        BOTH = "BOTH", "Ambas"

    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="psychologist_profile"
    )

    license_number = models.CharField(max_length=50, unique=True)
    specialty = models.CharField(max_length=150, blank=True)
    professional_phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True)

    attention_mode = models.CharField(
        max_length=20,
        choices=AttentionMode.choices,
        default=AttentionMode.BOTH
    )

    is_available_for_appointments = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.account and self.account.role != Account.Role.PSYCHOLOGIST:
            raise ValidationError({
                "account": "La cuenta seleccionada debe tener rol de psicólogo."
            })

    def __str__(self):
        return f"{self.account.first_name} {self.account.last_name}"