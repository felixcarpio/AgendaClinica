from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account
from apps.appointments.models import (
    Appointment,
    AvailabilitySlot,
)
from apps.clinical_records.models import (
    ClinicalRecord,
    SessionNote,
)
from apps.patients.models import Patient
from apps.psychologists.models import Psychologist


class SessionNoteModelTests(TestCase):
    """
    Pruebas de las reglas principales de ClinicalRecord
    y SessionNote.

    Se comprueba:
    - que cada paciente tenga un solo expediente;
    - que una nota pertenezca al paciente correcto;
    - que la cita haya finalizado;
    - que la cita se encuentre completada;
    - que cada cita tenga una sola nota;
    - que una nota válida pueda guardarse;
    - que una cita con nota clínica no pueda cancelarse.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Crea las cuentas y perfiles reutilizados
        durante todas las pruebas.
        """

        cls.psychologist_account = cls.create_account(
            email="clinical.psychologist@example.com",
            first_name="Laura",
            last_name="Psicóloga",
            role=Account.Role.PSYCHOLOGIST,
        )

        cls.patient_account = cls.create_account(
            email="clinical.patient@example.com",
            first_name="Carlos",
            last_name="Paciente",
            role=Account.Role.PATIENT,
        )

        cls.other_patient_account = cls.create_account(
            email="other.clinical.patient@example.com",
            first_name="Andrea",
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

        cls.other_patient = cls.create_profile(
            Patient,
            account=cls.other_patient_account,
        )

        cls.clinical_record = ClinicalRecord.objects.create(
            patient=cls.patient,
            chief_complaint="Motivo de consulta de prueba.",
        )

        cls.other_clinical_record = ClinicalRecord.objects.create(
            patient=cls.other_patient,
            chief_complaint="Otro motivo de consulta.",
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
        sus campos obligatorios.

        Los campos únicos reciben valores diferentes
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
        Genera un valor válido según el tipo del campo.
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
        duration_minutes=60,
    ):
        """
        Crea un cupo sin ejecutar la validación que impide
        registrar horarios pasados.

        Esto permite representar citas que ya ocurrieron,
        necesarias para probar notas clínicas.
        """

        start_time = (
            start_time
            or timezone.now() - timedelta(hours=2)
        )

        return AvailabilitySlot.objects.create(
            psychologist=self.psychologist,
            start_time=start_time,
            end_time=(
                start_time
                + timedelta(minutes=duration_minutes)
            ),
            status=AvailabilitySlot.Status.AVAILABLE,
        )

    def create_appointment(
        self,
        *,
        patient=None,
        status=Appointment.Status.COMPLETED,
        start_time=None,
    ):
        """
        Crea una cita utilizando las validaciones
        reales del modelo Appointment.
        """

        slot = self.create_slot(
            start_time=start_time,
        )

        return Appointment.objects.create(
            patient=patient or self.patient,
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
        clinical_record=None,
        appointment=None,
        session_summary="Resumen clínico de prueba.",
    ):
        """
        Crea y guarda una nota utilizando las validaciones
        reales del modelo SessionNote.
        """

        return SessionNote.objects.create(
            clinical_record=(
                clinical_record
                or self.clinical_record
            ),
            appointment=appointment,
            session_summary=session_summary,
            observations="Observaciones de prueba.",
            interventions="Intervenciones de prueba.",
            homework="Tarea de prueba.",
            next_session_plan="Plan de seguimiento.",
        )

    def test_patient_can_have_only_one_clinical_record(self):
        """
        La relación OneToOne debe impedir que un paciente
        tenga dos expedientes clínicos.
        """

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ClinicalRecord.objects.create(
                    patient=self.patient,
                    chief_complaint="Segundo expediente.",
                )

        self.assertEqual(
            ClinicalRecord.objects.filter(
                patient=self.patient,
            ).count(),
            1,
        )

    def test_valid_session_note_can_be_created(self):
        """
        Una cita completada y finalizada debe permitir
        registrar una nota clínica.
        """

        appointment = self.create_appointment()

        session_note = self.create_session_note(
            appointment=appointment,
        )

        self.assertIsNotNone(
            session_note.pk,
        )

        self.assertEqual(
            session_note.clinical_record,
            self.clinical_record,
        )

        self.assertEqual(
            session_note.appointment,
            appointment,
        )

        self.assertEqual(
            session_note.session_summary,
            "Resumen clínico de prueba.",
        )

    def test_session_note_requires_completed_appointment(self):
        """
        No debe permitirse registrar una nota
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

        with self.assertRaises(ValidationError) as context:
            session_note.save()

        self.assertIn(
            "appointment",
            context.exception.message_dict,
        )

        self.assertIn(
            "Solo es posible registrar notas para citas completadas.",
            context.exception.message_dict["appointment"],
        )

        self.assertEqual(
            SessionNote.objects.count(),
            0,
        )

    def test_confirmed_appointment_cannot_have_session_note(self):
        """
        Una cita confirmada todavía no debe permitir
        el registro de una nota clínica.
        """

        appointment = self.create_appointment(
            status=Appointment.Status.CONFIRMED,
        )

        session_note = SessionNote(
            clinical_record=self.clinical_record,
            appointment=appointment,
            session_summary="Resumen de prueba.",
        )

        with self.assertRaises(ValidationError) as context:
            session_note.save()

        self.assertIn(
            (
                "Solo es posible registrar notas "
                "para citas completadas."
            ),
            context.exception.message_dict["appointment"],
        )

    def test_future_appointment_cannot_have_session_note(self):
        """
        Aunque una cita se marque como completada,
        no debe aceptarse una nota mientras su horario
        todavía no haya finalizado.
        """

        future_start_time = (
            timezone.now()
            + timedelta(hours=1)
        )

        appointment = self.create_appointment(
            status=Appointment.Status.COMPLETED,
            start_time=future_start_time,
        )

        session_note = SessionNote(
            clinical_record=self.clinical_record,
            appointment=appointment,
            session_summary="Resumen de prueba.",
        )

        with self.assertRaises(ValidationError) as context:
            session_note.save()

        self.assertIn(
            "appointment",
            context.exception.message_dict,
        )

        self.assertIn(
            (
                "No es posible registrar una nota "
                "hasta que la cita haya finalizado."
            ),
            context.exception.message_dict["appointment"],
        )

    def test_appointment_must_belong_to_record_patient(self):
        """
        La cita seleccionada debe pertenecer al mismo
        paciente del expediente clínico.
        """

        other_patient_appointment = self.create_appointment(
            patient=self.other_patient,
        )

        session_note = SessionNote(
            clinical_record=self.clinical_record,
            appointment=other_patient_appointment,
            session_summary="Resumen de prueba.",
        )

        with self.assertRaises(ValidationError) as context:
            session_note.save()

        self.assertIn(
            "appointment",
            context.exception.message_dict,
        )

        self.assertIn(
            (
                "La cita seleccionada no pertenece al paciente "
                "del expediente clínico."
            ),
            context.exception.message_dict["appointment"],
        )

    def test_each_appointment_can_have_only_one_session_note(self):
        """
        La relación OneToOne debe impedir que una cita
        tenga dos notas de sesión.
        """

        appointment = self.create_appointment()

        self.create_session_note(
            appointment=appointment,
        )

        second_note = SessionNote(
            clinical_record=self.clinical_record,
            appointment=appointment,
            session_summary="Segunda nota de prueba.",
        )

        with self.assertRaises(ValidationError) as context:
            second_note.save()

        self.assertIn(
            "appointment",
            context.exception.message_dict,
        )

        self.assertEqual(
            SessionNote.objects.filter(
                appointment=appointment,
            ).count(),
            1,
        )

    def test_session_note_save_executes_model_validation(self):
        """
        El método save() debe ejecutar full_clean()
        antes de guardar la nota.
        """

        appointment = self.create_appointment(
            status=Appointment.Status.PENDING,
        )

        session_note = SessionNote(
            clinical_record=self.clinical_record,
            appointment=appointment,
            session_summary="Resumen de prueba.",
        )

        with self.assertRaises(ValidationError):
            session_note.save()

        self.assertIsNone(
            session_note.pk,
        )

    def test_appointment_with_session_note_cannot_be_cancelled(self):
        """
        Una cita que ya tiene una nota clínica
        no debe poder cancelarse.
        """

        appointment = self.create_appointment()

        self.create_session_note(
            appointment=appointment,
        )

        appointment.status = Appointment.Status.CANCELLED
        appointment.cancelled_reason = (
            "Intento de cancelación posterior."
        )

        with self.assertRaises(ValidationError) as context:
            appointment.save()

        self.assertIn(
            "status",
            context.exception.message_dict,
        )

        self.assertIn(
            (
                "No es posible cancelar una cita que ya tiene "
                "notas clínicas registradas."
            ),
            context.exception.message_dict["status"],
        )

        appointment.refresh_from_db()

        self.assertEqual(
            appointment.status,
            Appointment.Status.COMPLETED,
        )

    def test_clinical_record_string_representation(self):
        """
        La representación del expediente debe incluir
        al paciente relacionado.
        """

        self.assertEqual(
            str(self.clinical_record),
            f"Expediente clínico de {self.patient}",
        )

    def test_session_note_string_representation(self):
        """
        La representación de la nota debe incluir
        la cita relacionada.
        """

        appointment = self.create_appointment()

        session_note = self.create_session_note(
            appointment=appointment,
        )

        self.assertEqual(
            str(session_note),
            f"Nota de sesión - {appointment}",
        )