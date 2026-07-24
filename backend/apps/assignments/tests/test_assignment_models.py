from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Account
from apps.appointments.models import (
    Appointment,
    AvailabilitySlot,
)
from apps.assignments.models import (
    Assignment,
    AssignmentAttachment,
)
from apps.clinical_records.models import (
    ClinicalRecord,
    SessionNote,
)
from apps.patients.models import Patient
from apps.psychologists.models import Psychologist


class AssignmentTestBase(TestCase):
    """
    Pruebas de las reglas principales de Assignment.

    Se comprueba:
    - creación para citas completadas;
    - rechazo para citas no completadas;
    - visibilidad automática;
    - registro y eliminación de completed_at;
    - cancelación y reactivación;
    - representación de texto.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Crea las cuentas, perfiles y expediente clínico
        reutilizados durante las pruebas.
        """

        cls.psychologist_account = cls.create_account(
            email="assignment.psychologist@example.com",
            first_name="Laura",
            last_name="Psicóloga",
            role=Account.Role.PSYCHOLOGIST,
        )

        cls.patient_account = cls.create_account(
            email="assignment.patient@example.com",
            first_name="Carlos",
            last_name="Paciente",
            role=Account.Role.PATIENT,
        )

        cls.psychologist = cls.create_profile(
            Psychologist,
            account=cls.psychologist_account,
        )

        cls.patient = cls.create_profile(
            Patient,
            account=cls.patient_account,
        )

        cls.clinical_record = ClinicalRecord.objects.create(
            patient=cls.patient,
            chief_complaint="Motivo de consulta de prueba.",
        )

    @classmethod
    def create_account(
        cls,
        *,
        email,
        first_name,
        last_name,
        role,
    ):
        """
        Crea una cuenta válida para las pruebas.
        """

        account = Account(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
        )

        account.set_password("TestPassword123!")
        account.save()

        return account

    @classmethod
    def create_profile(
        cls,
        model_class,
        **overrides,
    ):
        """
        Crea un perfil completando automáticamente
        los campos obligatorios.

        Los campos únicos reciben valores distintos
        según la cuenta relacionada.
        """

        values = dict(overrides)

        related_account = values.get("account")

        unique_token = (
            related_account.pk
            if related_account and related_account.pk
            else model_class.objects.count() + 1
        )

        for field in model_class._meta.concrete_fields:
            if field.primary_key:
                continue

            if field.name in values:
                continue

            if getattr(field, "auto_now", False):
                continue

            if getattr(field, "auto_now_add", False):
                continue

            if field.has_default():
                continue

            if field.null or field.blank:
                continue

            if isinstance(
                field,
                (models.ForeignKey, models.OneToOneField),
            ):
                raise ValueError(
                    (
                        f"Debes proporcionar el campo relacionado "
                        f"obligatorio '{field.name}' para "
                        f"{model_class.__name__}."
                    )
                )

            values[field.name] = cls.build_field_value(
                field=field,
                model_class=model_class,
                unique_token=unique_token,
            )

        return model_class.objects.create(**values)

    @classmethod
    def build_field_value(
        cls,
        *,
        field,
        model_class,
        unique_token,
    ):
        """
        Genera un valor básico según el tipo del campo.
        """

        if field.choices:
            return field.choices[0][0]

        base_value = (
            f"{model_class.__name__.lower()}_"
            f"{field.name}"
        )

        if field.unique:
            base_value = f"{base_value}_{unique_token}"

        if isinstance(field, models.EmailField):
            return f"{base_value}@example.com"

        if isinstance(field, models.CharField):
            value = base_value

            if field.max_length:
                value = value[:field.max_length]

            return value

        if isinstance(field, models.TextField):
            return f"Valor de prueba para {field.name}"

        if isinstance(field, models.DateTimeField):
            return timezone.now()

        if isinstance(field, models.DateField):
            return date(
                2000,
                1,
                1,
            )

        if isinstance(field, models.BooleanField):
            return False

        if isinstance(field, models.DecimalField):
            return Decimal("1.00")

        if isinstance(
            field,
            (
                models.IntegerField,
                models.PositiveIntegerField,
                models.PositiveSmallIntegerField,
                models.SmallIntegerField,
            ),
        ):
            return unique_token if field.unique else 1

        if isinstance(field, models.FloatField):
            return (
                float(unique_token)
                if field.unique
                else 1.0
            )

        raise ValueError(
            (
                f"No se pudo generar automáticamente un valor "
                f"para el campo '{field.name}' de tipo "
                f"{field.__class__.__name__}."
            )
        )

    def create_slot(
        self,
        *,
        start_time=None,
    ):
        """
        Crea un cupo pasado para representar
        una sesión que ya ocurrió.
        """

        start_time = (
            start_time
            or timezone.now() - timedelta(hours=2)
        )

        return AvailabilitySlot.objects.create(
            psychologist=self.psychologist,
            start_time=start_time,
            end_time=start_time + timedelta(hours=1),
            status=AvailabilitySlot.Status.AVAILABLE,
        )

    def create_appointment(
        self,
        *,
        status=Appointment.Status.COMPLETED,
    ):
        """
        Crea una cita con el estado indicado.
        """

        slot = self.create_slot()

        return Appointment.objects.create(
            patient=self.patient,
            psychologist=self.psychologist,
            availability_slot=slot,
            status=status,
            reason="Consulta psicológica de prueba.",
            appointment_type=(
                Appointment.AppointmentType.IN_PERSON
            ),
        )

    def create_session_note(
        self,
        *,
        appointment_status=Appointment.Status.COMPLETED,
    ):
        """
        Crea una nota de sesión asociada a una cita.
        """

        appointment = self.create_appointment(
            status=appointment_status,
        )

        if appointment_status == Appointment.Status.COMPLETED:
            return SessionNote.objects.create(
                clinical_record=self.clinical_record,
                appointment=appointment,
                session_summary="Resumen clínico de prueba.",
                observations="Observaciones de prueba.",
            )

        return SessionNote.objects.create(
            clinical_record=self.clinical_record,
            appointment=appointment,
            session_summary="Resumen clínico de prueba.",
        )

    def create_assignment(
        self,
        *,
        session_note=None,
        status=Assignment.Status.PENDING,
        is_visible=True,
        completed_at=None,
    ):
        """
        Crea una asignación utilizando las validaciones
        reales del modelo.
        """

        session_note = (
            session_note
            or self.create_session_note()
        )

        return Assignment.objects.create(
            session_note=session_note,
            title="Registro de emociones",
            description=(
                "Registrar las emociones identificadas "
                "durante la semana."
            ),
            status=status,
            psychologist_comments=(
                "Completar antes de la próxima sesión."
            ),
            patient_response="",
            is_visible=is_visible,
            completed_at=completed_at,
        )
        
class AssignmentModelTests(AssignmentTestBase):
    """
    Pruebas de las reglas principales de Assignment.
    """
    def test_valid_assignment_can_be_created(self):
        """
        Una nota asociada a una cita completada
        debe permitir crear una asignación.
        """

        assignment = self.create_assignment()

        self.assertIsNotNone(
            assignment.pk,
        )

        self.assertEqual(
            assignment.status,
            Assignment.Status.PENDING,
        )

        self.assertTrue(
            assignment.is_visible,
        )

        self.assertIsNone(
            assignment.completed_at,
        )

    def test_assignment_requires_completed_appointment(self):
        """
        No debe permitirse crear una asignación
        para una cita pendiente.
        """

        appointment = self.create_appointment(
            status=Appointment.Status.PENDING,
        )

        session_note = SessionNote(
            clinical_record=self.clinical_record,
            appointment=appointment,
            session_summary="Resumen de prueba.",
        )

        assignment = Assignment(
            session_note=session_note,
            title="Asignación inválida",
            description="Descripción de prueba.",
        )

        with self.assertRaises(ValidationError) as context:
            assignment.full_clean()

        self.assertIn(
            "session_note",
            context.exception.message_dict,
        )

    def test_cancelled_assignment_becomes_hidden(self):
        """
        Una asignación cancelada debe ocultarse
        automáticamente para el paciente.
        """

        assignment = self.create_assignment()

        assignment.status = Assignment.Status.CANCELLED
        assignment.save()

        assignment.refresh_from_db()

        self.assertEqual(
            assignment.status,
            Assignment.Status.CANCELLED,
        )

        self.assertFalse(
            assignment.is_visible,
        )

        self.assertIsNone(
            assignment.completed_at,
        )

    def test_manual_visibility_is_ignored_when_cancelled(self):
        """
        Aunque se intente guardar una asignación cancelada
        como visible, el modelo debe ocultarla.
        """

        assignment = self.create_assignment(
            status=Assignment.Status.CANCELLED,
            is_visible=True,
        )

        assignment.refresh_from_db()

        self.assertFalse(
            assignment.is_visible,
        )

    def test_reactivated_assignment_becomes_visible(self):
        """
        Una asignación cancelada que vuelve a estado pendiente
        debe mostrarse nuevamente.
        """

        assignment = self.create_assignment(
            status=Assignment.Status.CANCELLED,
        )

        self.assertFalse(
            assignment.is_visible,
        )

        assignment.status = Assignment.Status.PENDING
        assignment.save()

        assignment.refresh_from_db()

        self.assertEqual(
            assignment.status,
            Assignment.Status.PENDING,
        )

        self.assertTrue(
            assignment.is_visible,
        )

    def test_completed_assignment_sets_completed_at(self):
        """
        Al completar una asignación debe registrarse
        automáticamente la fecha de finalización.
        """

        assignment = self.create_assignment()

        before_completion = timezone.now()

        assignment.status = Assignment.Status.COMPLETED
        assignment.save()

        after_completion = timezone.now()

        assignment.refresh_from_db()

        self.assertEqual(
            assignment.status,
            Assignment.Status.COMPLETED,
        )

        self.assertIsNotNone(
            assignment.completed_at,
        )

        self.assertGreaterEqual(
            assignment.completed_at,
            before_completion,
        )

        self.assertLessEqual(
            assignment.completed_at,
            after_completion,
        )

        self.assertTrue(
            assignment.is_visible,
        )

    def test_existing_completed_at_is_preserved(self):
        """
        Si una asignación completada ya tiene fecha,
        no debe reemplazarse al volver a guardarla.
        """

        original_completed_at = (
            timezone.now() - timedelta(days=1)
        )

        assignment = self.create_assignment(
            status=Assignment.Status.COMPLETED,
            completed_at=original_completed_at,
        )

        assignment.psychologist_comments = (
            "Comentario actualizado."
        )
        assignment.save()

        assignment.refresh_from_db()

        self.assertEqual(
            assignment.completed_at,
            original_completed_at,
        )

    def test_leaving_completed_status_clears_completed_at(self):
        """
        Si una asignación deja de estar completada,
        debe eliminarse la fecha de finalización.
        """

        assignment = self.create_assignment(
            status=Assignment.Status.COMPLETED,
        )

        self.assertIsNotNone(
            assignment.completed_at,
        )

        assignment.status = Assignment.Status.IN_PROGRESS
        assignment.save()

        assignment.refresh_from_db()

        self.assertEqual(
            assignment.status,
            Assignment.Status.IN_PROGRESS,
        )

        self.assertIsNone(
            assignment.completed_at,
        )

        self.assertTrue(
            assignment.is_visible,
        )

    def test_pending_assignment_cannot_keep_completed_at(self):
        """
        Una asignación pendiente no debe conservar
        manualmente una fecha de finalización.
        """

        manual_completed_at = (
            timezone.now() - timedelta(hours=1)
        )

        assignment = self.create_assignment(
            status=Assignment.Status.PENDING,
            completed_at=manual_completed_at,
        )

        assignment.refresh_from_db()

        self.assertIsNone(
            assignment.completed_at,
        )

    def test_assignment_save_executes_validation(self):
        """
        El método save() debe ejecutar full_clean()
        antes de guardar.
        """

        appointment = self.create_appointment(
            status=Appointment.Status.PENDING,
        )

        session_note = SessionNote(
            clinical_record=self.clinical_record,
            appointment=appointment,
            session_summary="Resumen de prueba.",
        )

        assignment = Assignment(
            session_note=session_note,
            title="Asignación inválida",
            description="Descripción inválida.",
        )

        with self.assertRaises(ValidationError):
            assignment.save()

        self.assertIsNone(
            assignment.pk,
        )

    def test_assignment_string_representation(self):
        """
        La representación de texto debe incluir
        el título y el paciente.
        """

        assignment = self.create_assignment()

        self.assertEqual(
            str(assignment),
            f"{assignment.title} - {self.patient}",
        )


class AssignmentAttachmentModelTests(AssignmentTestBase):
    """
    Pruebas para los archivos adjuntos de las asignaciones.

    Se comprueba:
    - guardado del nombre original;
    - conservación de un nombre personalizado;
    - representación de texto;
    - eliminación en cascada.
    """

    def setUp(self):
        """
        Crea un directorio temporal para evitar guardar
        archivos de prueba dentro del proyecto.
        """

        self.temporary_media = TemporaryDirectory()
        self.media_override = override_settings(
            MEDIA_ROOT=self.temporary_media.name,
        )
        self.media_override.enable()

    def tearDown(self):
        """
        Restaura la configuración y elimina
        los archivos temporales.
        """

        self.media_override.disable()
        self.temporary_media.cleanup()

    def create_attachment(
        self,
        *,
        assignment=None,
        filename="registro_emociones.pdf",
        uploaded_by=(
            AssignmentAttachment.UploadedBy.PATIENT
        ),
        original_name="",
    ):
        """
        Crea un archivo adjunto de prueba.
        """

        assignment = (
            assignment
            or self.create_assignment()
        )

        uploaded_file = SimpleUploadedFile(
            name=filename,
            content=b"Contenido de archivo de prueba.",
            content_type="application/pdf",
        )

        return AssignmentAttachment.objects.create(
            assignment=assignment,
            file=uploaded_file,
            uploaded_by=uploaded_by,
            original_name=original_name,
        )

    def test_attachment_stores_original_filename(self):
        """
        El modelo debe conservar automáticamente
        el nombre original del archivo.
        """

        attachment = self.create_attachment(
            filename="actividad_semanal.pdf",
        )

        attachment.refresh_from_db()

        self.assertEqual(
            attachment.original_name,
            "actividad_semanal.pdf",
        )

    def test_custom_original_name_is_preserved(self):
        """
        Si ya se proporciona un nombre original,
        el modelo no debe reemplazarlo.
        """

        attachment = self.create_attachment(
            filename="archivo_interno.pdf",
            original_name="Documento del paciente.pdf",
        )

        attachment.refresh_from_db()

        self.assertEqual(
            attachment.original_name,
            "Documento del paciente.pdf",
        )

    def test_attachment_file_is_saved_in_media_directory(self):
        """
        El archivo debe guardarse dentro de la ruta
        configurada para adjuntos de asignaciones.
        """

        attachment = self.create_attachment()

        self.assertTrue(
            Path(attachment.file.path).exists(),
        )

        self.assertIn(
            "assignments",
            attachment.file.name,
        )

        self.assertIn(
            "attachments",
            attachment.file.name,
        )

    def test_attachment_string_representation(self):
        """
        La representación de texto debe incluir
        el nombre original y la asignación.
        """

        attachment = self.create_attachment(
            filename="respuesta_paciente.pdf",
        )

        self.assertEqual(
            str(attachment),
            (
                f"respuesta_paciente.pdf - "
                f"{attachment.assignment}"
            ),
        )

    def test_attachment_can_be_uploaded_by_psychologist(self):
        """
        Un archivo puede registrarse como material
        proporcionado por el psicólogo.
        """

        attachment = self.create_attachment(
            uploaded_by=(
                AssignmentAttachment.UploadedBy.PSYCHOLOGIST
            ),
        )

        self.assertEqual(
            attachment.uploaded_by,
            AssignmentAttachment.UploadedBy.PSYCHOLOGIST,
        )

    def test_deleting_assignment_deletes_attachments(self):
        """
        Al eliminar una asignación deben eliminarse
        sus registros de archivos adjuntos.
        """

        assignment = self.create_assignment()

        attachment = self.create_attachment(
            assignment=assignment,
        )

        attachment_pk = attachment.pk

        assignment.delete()

        self.assertFalse(
            AssignmentAttachment.objects.filter(
                pk=attachment_pk,
            ).exists(),
        )