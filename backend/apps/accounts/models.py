from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError

from .managers import AccountManager


class Account(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        ASSISTANT = "ASSISTANT", "Asistente"
        PSYCHOLOGIST = "PSYCHOLOGIST", "Psicólogo"
        PATIENT = "PATIENT", "Paciente"

    email = models.EmailField(unique=True,verbose_name="Correo electrónico")
    first_name = models.CharField(max_length=20,verbose_name="Nombre")
    last_name = models.CharField(max_length=20,verbose_name="Apellido")
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]


    def clean(self):
        if not self.pk:
            return

        old_account = Account.objects.get(pk=self.pk)

        if old_account.role != self.role:
            if hasattr(self, "patient_profile"):
                raise ValidationError({
                    "role": "No puedes cambiar el rol porque esta cuenta ya tiene un perfil de paciente."
                })

            if hasattr(self, "psychologist_profile"):
                raise ValidationError({
                    "role": "No puedes cambiar el rol porque esta cuenta ya tiene un perfil de psicólogo."
                })


    def __str__(self):
        return self.email