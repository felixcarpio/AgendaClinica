from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

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

    def __str__(self):
        return self.email