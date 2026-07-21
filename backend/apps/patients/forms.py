from django import forms
from django.utils import timezone

from apps.accounts.models import Account
from apps.patients.models import (
    Patient,
    PatientPsychologistRelationship,
)


class PsychologistPatientCreateForm(forms.Form):
    """
    Formulario utilizado por el psicólogo para registrar
    un paciente nuevo.

    Reúne en una sola pantalla la información necesaria para:

    - Crear la cuenta del paciente.
    - Crear su perfil de paciente.
    - Crear la relación con el psicólogo.
    - Crear su expediente clínico inicial.

    La creación de los objetos se realizará posteriormente
    desde la vista dentro de una transacción atómica.
    """

    first_name = forms.CharField(
        label="Nombre",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa el nombre",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        label="Apellido",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa el apellido",
                "autocomplete": "family-name",
            }
        ),
    )

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "paciente@correo.com",
                "autocomplete": "email",
            }
        ),
        help_text=(
            "Este correo será utilizado por el paciente "
            "para iniciar sesión en el sistema."
        ),
    )

    phone = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Número de teléfono",
                "autocomplete": "tel",
            }
        ),
    )

    birth_date = forms.DateField(
        label="Fecha de nacimiento",
        required=False,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
    )

    gender = forms.ChoiceField(
        label="Género",
        required=False,
        choices=[
            ("", "Selecciona una opción"),
            *Patient.Gender.choices,
        ],
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    address = forms.CharField(
        label="Dirección",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Dirección del paciente",
                "rows": 3,
            }
        ),
    )

    emergency_contact_name = forms.CharField(
        label="Nombre del contacto de emergencia",
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Nombre completo",
            }
        ),
    )

    emergency_contact_phone = forms.CharField(
        label="Teléfono del contacto de emergencia",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Número de teléfono",
                "autocomplete": "tel",
            }
        ),
    )

    chief_complaint = forms.CharField(
        label="Motivo de consulta",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": (
                    "Describe brevemente la razón principal "
                    "por la que inicia el proceso terapéutico"
                ),
                "rows": 5,
            }
        ),
        help_text=(
            "Esta información se guardará en el expediente "
            "clínico inicial del paciente."
        ),
    )

    def clean_first_name(self):
        """
        Elimina espacios innecesarios del nombre.
        """

        first_name = self.cleaned_data["first_name"].strip()

        if not first_name:
            raise forms.ValidationError(
                "Debes ingresar el nombre del paciente."
            )

        return first_name

    def clean_last_name(self):
        """
        Elimina espacios innecesarios del apellido.
        """

        last_name = self.cleaned_data["last_name"].strip()

        if not last_name:
            raise forms.ValidationError(
                "Debes ingresar el apellido del paciente."
            )

        return last_name

    def clean_email(self):
        """
        Normaliza el correo y evita crear cuentas duplicadas.
        """

        email = self.cleaned_data["email"].strip().lower()

        if Account.objects.filter(
            email__iexact=email,
        ).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este correo."
            )

        return email

    def clean_birth_date(self):
        """
        Evita registrar fechas de nacimiento futuras.
        """

        birth_date = self.cleaned_data.get("birth_date")

        if (
            birth_date
            and birth_date > timezone.localdate()
        ):
            raise forms.ValidationError(
                "La fecha de nacimiento no puede estar en el futuro."
            )

        return birth_date

    def clean(self):
        """
        Valida que los datos del contacto de emergencia
        sean coherentes entre sí.
        """

        cleaned_data = super().clean()

        emergency_contact_name = (
            cleaned_data
            .get("emergency_contact_name", "")
            .strip()
        )

        emergency_contact_phone = (
            cleaned_data
            .get("emergency_contact_phone", "")
            .strip()
        )

        if (
            emergency_contact_phone
            and not emergency_contact_name
        ):
            self.add_error(
                "emergency_contact_name",
                (
                    "Debes indicar el nombre del contacto "
                    "de emergencia."
                ),
            )

        if (
            emergency_contact_name
            and not emergency_contact_phone
        ):
            self.add_error(
                "emergency_contact_phone",
                (
                    "Debes indicar el teléfono del contacto "
                    "de emergencia."
                ),
            )

        cleaned_data["emergency_contact_name"] = (
            emergency_contact_name
        )

        cleaned_data["emergency_contact_phone"] = (
            emergency_contact_phone
        )

        return cleaned_data
    
class PsychologistPatientStatusForm(forms.Form):
    """
    Permite al psicólogo actualizar el estado de atención
    de un paciente vinculado.

    El estado pertenece a la relación paciente-psicólogo,
    porque un mismo paciente podría ser atendido por
    diferentes profesionales en distintos momentos.
    """

    status = forms.ChoiceField(
        label="Estado del paciente",
        choices=(
            (
                PatientPsychologistRelationship.Status.ACTIVE,
                "Activo",
            ),
            (
                PatientPsychologistRelationship.Status.INACTIVE,
                "Inactivo",
            ),
            (
                PatientPsychologistRelationship.Status.DISCHARGED,
                "Dado de alta",
            ),
        ),
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    def __init__(self, *args, relationship=None, **kwargs):
        """
        Recibe la relación actual para mostrar su estado
        como valor inicial.
        """

        super().__init__(*args, **kwargs)

        self.relationship = relationship

        if relationship is not None:
            self.fields["status"].initial = relationship.status

    def clean_status(self):
        """
        Verifica que el estado recibido sea uno de los
        valores permitidos.
        """

        status = self.cleaned_data["status"]

        allowed_statuses = {
            PatientPsychologistRelationship.Status.ACTIVE,
            PatientPsychologistRelationship.Status.INACTIVE,
            PatientPsychologistRelationship.Status.DISCHARGED,
        }

        if status not in allowed_statuses:
            raise forms.ValidationError(
                "El estado seleccionado no es válido."
            )

        return status