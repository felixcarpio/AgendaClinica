from django import forms
from django.db.models import Q

from apps.appointments.models import Appointment
from apps.clinical_records.models import SessionNote

from .models import Assignment, AssignmentAttachment
from pathlib import Path


class AssignmentPsychologistForm(forms.ModelForm):
    """
    Formulario utilizado por el psicólogo para crear y administrar
    asignaciones terapéuticas.

    El psicólogo puede modificar las instrucciones, comentarios y estado,
    pero no la respuesta escrita por el paciente.
    """

    class Meta:
        model = Assignment
        fields = (
            "session_note",
            "title",
            "description",
            "status",
            "psychologist_comments",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Solo se muestran notas asociadas a citas completadas.
        notes = SessionNote.objects.filter(
            appointment__status=Appointment.Status.COMPLETED
        ).select_related(
            "clinical_record__patient",
            "appointment__availability_slot",
        ).order_by(
            "-appointment__availability_slot__start_time"
        )

        # Al editar una asignación, también se conserva
        # la nota actualmente relacionada.
        if self.instance and self.instance.pk:
            notes = SessionNote.objects.filter(
                Q(
                    appointment__status=Appointment.Status.COMPLETED
                )
                | Q(pk=self.instance.session_note_id)
            ).select_related(
                "clinical_record__patient",
                "appointment__availability_slot",
            ).order_by(
                "-appointment__availability_slot__start_time"
            )

        self.fields["session_note"].queryset = notes


class AssignmentPatientForm(forms.ModelForm):
    """
    Formulario utilizado por el paciente para responder y actualizar
    el progreso de una asignación.

    El paciente no puede modificar las instrucciones, cancelarla
    ni reabrir una asignación completada.
    """

    class Meta:
        model = Assignment
        fields = (
            "patient_response",
            "status",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_status = self.instance.status

        # Las opciones disponibles dependen del estado actual.
        allowed_choices = {
            Assignment.Status.PENDING: (
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
            ),
            Assignment.Status.IN_PROGRESS: (
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
            ),
            Assignment.Status.COMPLETED: (
                Assignment.Status.COMPLETED,
            ),
            Assignment.Status.CANCELLED: (
                Assignment.Status.CANCELLED,
            ),
        }

        allowed_values = allowed_choices.get(current_status, ())

        self.fields["status"].choices = [
            choice
            for choice in Assignment.Status.choices
            if choice[0] in allowed_values
        ]

    def clean_status(self):
        """
        Valida que el paciente únicamente realice transiciones
        de estado permitidas.
        """

        new_status = self.cleaned_data["status"]
        current_status = self.instance.status

        allowed_transitions = {
            Assignment.Status.PENDING: {
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
            },
            Assignment.Status.IN_PROGRESS: {
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
            },
            Assignment.Status.COMPLETED: {
                Assignment.Status.COMPLETED,
            },
            Assignment.Status.CANCELLED: {
                Assignment.Status.CANCELLED,
            },
        }

        if new_status not in allowed_transitions.get(current_status, set()):
            raise forms.ValidationError(
                "No tienes permiso para realizar este cambio de estado."
            )

        return new_status
    
class PatientAssignmentResponseForm(forms.ModelForm):
    """
    Permite al paciente responder una asignación
    y actualizar su progreso.
    """

    class Meta:
        model = Assignment
        fields = [
            "patient_response",
            "status",
        ]

        widgets = {
            "patient_response": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": (
                        "Escribe aquí tu respuesta, reflexión "
                        "o resultado de la actividad."
                    ),
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
        }

        labels = {
            "patient_response": "Mi respuesta",
            "status": "Estado de la actividad",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # El paciente únicamente puede manejar estos estados.
        self.fields["status"].choices = [
            (
                Assignment.Status.PENDING,
                Assignment.Status.PENDING.label,
            ),
            (
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.IN_PROGRESS.label,
            ),
            (
                Assignment.Status.COMPLETED,
                Assignment.Status.COMPLETED.label,
            ),
        ]

    def clean_patient_response(self):
        """
        Limpia espacios innecesarios de la respuesta.
        """

        response = self.cleaned_data.get(
            "patient_response",
            ""
        ).strip()

        return response

    def clean(self):
        """
        Una asignación completada debe incluir
        una respuesta del paciente.
        """

        cleaned_data = super().clean()

        status = cleaned_data.get("status")
        response = cleaned_data.get(
            "patient_response",
            ""
        )

        if (
            status == Assignment.Status.COMPLETED
            and not response
        ):
            self.add_error(
                "patient_response",
                (
                    "Debes escribir una respuesta antes "
                    "de marcar la asignación como completada."
                ),
            )

        return cleaned_data
    
class PsychologistAssignmentForm(forms.ModelForm):
    """
    Formulario utilizado por el psicólogo para crear o actualizar
    una asignación desde una nota de sesión.

    La nota de sesión se asigna desde la vista para evitar que
    el psicólogo pueda vincular la actividad manualmente
    con una sesión diferente.
    """

    class Meta:
        model = Assignment
        fields = [
            "title",
            "description",
            "status",
            "psychologist_comments",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Escribe el título de la actividad.",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": (
                        "Describe las instrucciones que debe "
                        "seguir el paciente."
                    ),
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "psychologist_comments": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": (
                        "Agrega comentarios o recomendaciones "
                        "adicionales para el paciente."
                    ),
                }
            ),
        }

        labels = {
            "title": "Título",
            "description": "Descripción e instrucciones",
            "status": "Estado",
            "psychologist_comments": "Comentarios del psicólogo",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        current_status = (
            self.instance.status
            if self.instance and self.instance.pk
            else Assignment.Status.PENDING
        )

        allowed_choices = {
            Assignment.Status.PENDING: (
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
                Assignment.Status.CANCELLED,
            ),
            Assignment.Status.IN_PROGRESS: (
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
                Assignment.Status.CANCELLED,
            ),
            Assignment.Status.COMPLETED: (
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
                Assignment.Status.COMPLETED,
                Assignment.Status.CANCELLED,
            ),
            Assignment.Status.CANCELLED: (
                Assignment.Status.CANCELLED,
                Assignment.Status.PENDING,
            ),
        }

        allowed_values = allowed_choices.get(
            current_status,
            (),
        )

        self.fields["status"].choices = [
            choice
            for choice in Assignment.Status.choices
            if choice[0] in allowed_values
        ]

    def clean_title(self):
        """
        Evita guardar títulos vacíos o compuestos únicamente
        por espacios.
        """

        title = self.cleaned_data["title"].strip()

        if not title:
            raise forms.ValidationError(
                "Debes ingresar un título para la asignación."
            )

        return title

    def clean_description(self):
        """
        Evita guardar instrucciones vacías.
        """

        description = self.cleaned_data["description"].strip()

        if not description:
            raise forms.ValidationError(
                "Debes ingresar las instrucciones de la asignación."
            )

        return description

    def clean_status(self):
        """
        Impide que una asignación cancelada sea reabierta
        directamente en un estado distinto de pendiente.
        """

        new_status = self.cleaned_data["status"]

        if not self.instance or not self.instance.pk:
            return new_status

        current_status = (
            Assignment.objects
            .filter(pk=self.instance.pk)
            .values_list("status", flat=True)
            .first()
        )

        if (
            current_status == Assignment.Status.CANCELLED
            and new_status not in {
                Assignment.Status.CANCELLED,
                Assignment.Status.PENDING,
            }
        ):
            raise forms.ValidationError(
                "Una asignación cancelada debe reabrirse primero como pendiente."
            )

        return new_status
    
class PsychologistAssignmentAttachmentForm(forms.ModelForm):
    """
    Permite al psicólogo adjuntar material de apoyo
    a una asignación terapéutica.

    La asignación y el usuario que sube el archivo
    se establecen desde la vista.
    """

    class Meta:
        model = AssignmentAttachment
        fields = [
            "file",
        ]

        widgets = {
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": (
                        ".pdf,.doc,.docx,.txt,"
                        ".jpg,.jpeg,.png"
                    ),
                }
            ),
        }

        labels = {
            "file": "Archivo adjunto",
        }

    def clean_file(self):
        """
        Valida el tamaño y la extensión del archivo.
        """

        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            return uploaded_file

        max_size = 10 * 1024 * 1024

        if uploaded_file.size > max_size:
            raise forms.ValidationError(
                "El archivo no puede superar los 10 MB."
            )

        allowed_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
        }

        extension = Path(
            uploaded_file.name
        ).suffix.lower()

        if extension not in allowed_extensions:
            raise forms.ValidationError(
                (
                    "Formato no permitido. Puedes subir archivos "
                    "PDF, Word, TXT, JPG o PNG."
                )
            )

        return uploaded_file
    
class PatientAssignmentAttachmentForm(forms.ModelForm):
    """
    Permite al paciente adjuntar un archivo como parte
    de su respuesta a una asignación terapéutica.

    La asignación y el tipo de usuario que realiza la carga
    se establecen desde la vista.
    """

    class Meta:
        model = AssignmentAttachment
        fields = [
            "file",
        ]

        widgets = {
            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": (
                        ".pdf,.doc,.docx,.txt,"
                        ".jpg,.jpeg,.png"
                    ),
                }
            ),
        }

        labels = {
            "file": "Archivo de respuesta",
        }

    def clean_file(self):
        """
        Valida el tamaño y la extensión del archivo enviado.
        """

        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            return uploaded_file

        max_size = 10 * 1024 * 1024

        if uploaded_file.size > max_size:
            raise forms.ValidationError(
                "El archivo no puede superar los 10 MB."
            )

        allowed_extensions = {
            ".pdf",
            ".doc",
            ".docx",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
        }

        extension = Path(uploaded_file.name).suffix.lower()

        if extension not in allowed_extensions:
            raise forms.ValidationError(
                (
                    "Formato no permitido. Puedes subir archivos "
                    "PDF, Word, TXT, JPG o PNG."
                )
            )

        return uploaded_file