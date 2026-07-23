from django import forms

from apps.accounts.models import Account
from apps.psychologists.models import Psychologist


class AdminPsychologistCreateForm(forms.Form):
    """
    Formulario utilizado por un administrador para registrar
    una cuenta y un perfil profesional de psicólogo.

    La creación de Account y Psychologist se realiza desde la vista
    dentro de una única transacción.
    """

    first_name = forms.CharField(
        max_length=150,
        label="Nombres",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa los nombres.",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        label="Apellidos",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa los apellidos.",
                "autocomplete": "family-name",
            }
        ),
    )

    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "nombre@correo.com",
                "autocomplete": "email",
            }
        ),
    )

    gender = forms.ChoiceField(
        choices=Psychologist.Gender.choices,
        label="Género",
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    license_number = forms.CharField(
        max_length=50,
        label="Número de licencia",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa el número de licencia profesional.",
            }
        ),
    )

    specialty = forms.CharField(
        max_length=150,
        required=False,
        label="Especialidad",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ejemplo: Psicología clínica.",
            }
        ),
    )

    professional_phone = forms.CharField(
        max_length=20,
        required=False,
        label="Teléfono profesional",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa el número de contacto.",
                "autocomplete": "tel",
            }
        ),
    )

    attention_mode = forms.ChoiceField(
        choices=Psychologist.AttentionMode.choices,
        label="Modalidad de atención",
        widget=forms.Select(
            attrs={
                "class": "form-control",
            }
        ),
    )

    bio = forms.CharField(
        required=False,
        label="Perfil profesional",
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": (
                    "Describe brevemente la experiencia, "
                    "formación o enfoque profesional."
                ),
            }
        ),
    )

    is_available_for_appointments = forms.BooleanField(
        required=False,
        initial=True,
        label="Disponible para recibir citas",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-checkbox",
            }
        ),
    )

    def clean_first_name(self):
        """
        Elimina espacios innecesarios y evita nombres vacíos.
        """

        first_name = self.cleaned_data["first_name"].strip()

        if not first_name:
            raise forms.ValidationError(
                "Debes ingresar los nombres del psicólogo."
            )

        return first_name

    def clean_last_name(self):
        """
        Elimina espacios innecesarios y evita apellidos vacíos.
        """

        last_name = self.cleaned_data["last_name"].strip()

        if not last_name:
            raise forms.ValidationError(
                "Debes ingresar los apellidos del psicólogo."
            )

        return last_name

    def clean_email(self):
        """
        Evita registrar dos cuentas con el mismo correo.
        """

        email = self.cleaned_data["email"].strip().lower()

        if Account.objects.filter(
            email__iexact=email,
        ).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta registrada con este correo."
            )

        return email

    def clean_license_number(self):
        """
        Evita registrar dos psicólogos con la misma licencia.
        """

        license_number = (
            self.cleaned_data["license_number"]
            .strip()
        )

        if not license_number:
            raise forms.ValidationError(
                "Debes ingresar el número de licencia."
            )

        if Psychologist.objects.filter(
            license_number__iexact=license_number,
        ).exists():
            raise forms.ValidationError(
                "Ya existe un psicólogo registrado con esta licencia."
            )

        return license_number

    def clean_specialty(self):
        """
        Limpia espacios innecesarios de la especialidad.
        """

        return self.cleaned_data.get(
            "specialty",
            "",
        ).strip()

    def clean_professional_phone(self):
        """
        Limpia espacios innecesarios del teléfono.
        """

        return self.cleaned_data.get(
            "professional_phone",
            "",
        ).strip()

    def clean_bio(self):
        """
        Limpia espacios innecesarios del perfil profesional.
        """

        return self.cleaned_data.get(
            "bio",
            "",
        ).strip()
        
class AdminPsychologistUpdateForm(forms.ModelForm):
    """
    Formulario utilizado por el administrador para actualizar
    la información profesional de un psicólogo existente.

    Los datos de acceso de la cuenta, como correo electrónico,
    contraseña y rol, no se modifican desde este formulario.
    """

    first_name = forms.CharField(
        max_length=150,
        label="Nombres",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa los nombres.",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        max_length=150,
        label="Apellidos",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa los apellidos.",
                "autocomplete": "family-name",
            }
        ),
    )

    class Meta:
        model = Psychologist

        fields = (
            "first_name",
            "last_name",
            "gender",
            "license_number",
            "specialty",
            "professional_phone",
            "attention_mode",
            "bio",
            "is_available_for_appointments",
        )

        widgets = {
            "gender": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "license_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Ingresa el número de licencia profesional."
                    ),
                }
            ),
            "specialty": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ejemplo: Psicología clínica.",
                }
            ),
            "professional_phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ingresa el número de contacto.",
                    "autocomplete": "tel",
                }
            ),
            "attention_mode": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": (
                        "Describe brevemente la experiencia, "
                        "formación o enfoque profesional."
                    ),
                }
            ),
            "is_available_for_appointments": (
                forms.CheckboxInput(
                    attrs={
                        "class": "form-checkbox",
                    }
                )
            ),
        }

        labels = {
            "gender": "Género",
            "license_number": "Número de licencia",
            "specialty": "Especialidad",
            "professional_phone": "Teléfono profesional",
            "attention_mode": "Modalidad de atención",
            "bio": "Perfil profesional",
            "is_available_for_appointments": (
                "Disponible para recibir citas"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Los nombres pertenecen al modelo Account,
        # por lo que se cargan manualmente desde la cuenta
        # asociada al psicólogo.
        if self.instance and self.instance.pk:
            self.fields["first_name"].initial = (
                self.instance.account.first_name
            )

            self.fields["last_name"].initial = (
                self.instance.account.last_name
            )

    def clean_first_name(self):
        """
        Elimina espacios innecesarios y evita nombres vacíos.
        """

        first_name = self.cleaned_data["first_name"].strip()

        if not first_name:
            raise forms.ValidationError(
                "Debes ingresar los nombres del psicólogo."
            )

        return first_name

    def clean_last_name(self):
        """
        Elimina espacios innecesarios y evita apellidos vacíos.
        """

        last_name = self.cleaned_data["last_name"].strip()

        if not last_name:
            raise forms.ValidationError(
                "Debes ingresar los apellidos del psicólogo."
            )

        return last_name

    def clean_license_number(self):
        """
        Evita asignar una licencia que ya pertenezca
        a otro psicólogo.
        """

        license_number = (
            self.cleaned_data["license_number"]
            .strip()
        )

        if not license_number:
            raise forms.ValidationError(
                "Debes ingresar el número de licencia."
            )

        duplicated_license = (
            Psychologist.objects
            .filter(
                license_number__iexact=license_number,
            )
            .exclude(
                pk=self.instance.pk,
            )
            .exists()
        )

        if duplicated_license:
            raise forms.ValidationError(
                "Ya existe otro psicólogo registrado con esta licencia."
            )

        return license_number

    def clean_specialty(self):
        """
        Limpia espacios innecesarios de la especialidad.
        """

        return self.cleaned_data.get(
            "specialty",
            "",
        ).strip()

    def clean_professional_phone(self):
        """
        Limpia espacios innecesarios del teléfono.
        """

        return self.cleaned_data.get(
            "professional_phone",
            "",
        ).strip()

    def clean_bio(self):
        """
        Limpia espacios innecesarios del perfil profesional.
        """

        return self.cleaned_data.get(
            "bio",
            "",
        ).strip()

    def save(self, commit=True):
        """
        Actualiza los datos profesionales del psicólogo
        y los nombres almacenados en su cuenta.
        """

        psychologist = super().save(
            commit=False,
        )

        account = psychologist.account
        account.first_name = self.cleaned_data["first_name"]
        account.last_name = self.cleaned_data["last_name"]

        if commit:
            account.full_clean()
            account.save(
                update_fields=[
                    "first_name",
                    "last_name",
                ]
            )

            psychologist.save()

        return psychologist