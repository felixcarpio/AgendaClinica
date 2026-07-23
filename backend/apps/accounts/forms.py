from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from apps.accounts.models import Account


class AccountAuthenticationForm(AuthenticationForm):
    """
    Formulario personalizado de inicio de sesión.

    Permite mostrar un mensaje específico cuando la cuenta existe,
    pero ha sido desactivada por un administrador.
    """

    username = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa tu correo electrónico",
                "autocomplete": "email",
                "autofocus": True,
            }
        ),
    )

    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ingresa tu contraseña",
                "autocomplete": "current-password",
            }
        ),
    )

    error_messages = {
        "invalid_login": (
            "El correo electrónico o la contraseña no son correctos."
        ),
        "inactive": (
            "Tu cuenta se encuentra inactiva. "
            "Comunícate con el administrador del sistema."
        ),
    }

    def clean(self):
        """
        Valida las credenciales y diferencia una cuenta inactiva
        de unas credenciales incorrectas.
        """

        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email and password:
            account = (
                Account.objects
                .filter(email__iexact=email.strip())
                .first()
            )

            # Solo mostramos el mensaje de cuenta inactiva cuando
            # la contraseña ingresada corresponde a esa cuenta.
            # Esto evita revelar el estado de una cuenta únicamente
            # conociendo su correo electrónico.
            if (
                account
                and not account.is_active
                and account.check_password(password)
            ):
                raise ValidationError(
                    self.error_messages["inactive"],
                    code="inactive",
                )

            self.user_cache = authenticate(
                self.request,
                username=email,
                password=password,
            )

            if self.user_cache is None:
                raise self.get_invalid_login_error()

            self.confirm_login_allowed(
                self.user_cache,
            )

        return self.cleaned_data