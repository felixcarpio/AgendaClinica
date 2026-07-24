from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account
from apps.appointments.models import (
    Appointment,
    AvailabilitySlot,
)
from apps.patients.models import Patient
from apps.psychologists.models import Psychologist


class AppointmentModelTests(TestCase):
    """
    Pruebas de las reglas principales del modelo Appointment.

    Se comprueba:
    - la reserva automática de cupos;
    - la prevención de doble reserva;
    - la validación del psicólogo propietario;
    - la cancelación con motivo obligatorio;
    - la liberación del cupo al cancelar;
    - la liberación y reserva de cupos al reprogramar;
    - las propiedades auxiliares de la cita.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Crea las cuentas, perfiles y fechas base reutilizadas
        por todas las pruebas.
        """

        cls.psychologist_account = cls.create_account(
            email="psychologist.appointments@example.com",
            first_name="Laura",
            last_name="Psicóloga",
            role=Account.Role.PSYCHOLOGIST,
        )

        cls.other_psychologist_account = cls.create_account(
            email="other.psychologist@example.com",
            first_name="Daniel",
            last_name="Psicólogo",
            role=Account.Role.PSYCHOLOGIST,
        )

        cls.patient_account = cls.create_account(
            email="patient.appointments@example.com",
            first_name="Carlos",
            last_name="Paciente",
            role=Account.Role.PATIENT,
        )

        cls.other_patient_account = cls.create_account(
            email="other.patient@example.com",
            first_name="Andrea",
            last_name="Paciente",
            role=Account.Role.PATIENT,
        )

        cls.psychologist = cls.create_profile(
            Psychologist,
            account=cls.psychologist_account,
        )

        cls.other_psychologist = cls.create_profile(
            Psychologist,
            account=cls.other_psychologist_account,
        )

        cls.patient = cls.create_profile(
            Patient,
            account=cls.patient_account,
        )

        cls.other_patient = cls.create_profile(
            Patient,
            account=cls.other_patient_account,
        )

        cls.base_start_time = timezone.make_aware(
            datetime(
                2030,
                7,
                20,
                9,
                0,
            )
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
        Crea una cuenta válida para utilizarla en las pruebas.
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
        Crea un perfil completando automáticamente cualquier
        campo obligatorio definido en Patient o Psychologist.

        Los campos únicos reciben un valor diferente según
        la cuenta relacionada, evitando datos duplicados.
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
        Genera un valor válido básico según el tipo del campo.

        Los campos marcados como únicos reciben un sufijo
        para evitar conflictos en la base de datos temporal.
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
            return timezone.make_aware(
                datetime(
                    2030,
                    1,
                    1,
                    8,
                    0,
                )
            )

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
        psychologist=None,
        start_time=None,
        duration_minutes=60,
        status=AvailabilitySlot.Status.AVAILABLE,
    ):
        """
        Crea un cupo de disponibilidad para las pruebas.
        """

        psychologist = (
            psychologist
            or self.psychologist
        )

        start_time = (
            start_time
            or self.base_start_time
        )

        return AvailabilitySlot.objects.create(
            psychologist=psychologist,
            start_time=start_time,
            end_time=(
                start_time
                + timedelta(minutes=duration_minutes)
            ),
            status=status,
        )

    def create_appointment(
        self,
        *,
        slot,
        patient=None,
        psychologist=None,
        status=Appointment.Status.PENDING,
        cancelled_reason="",
    ):
        """
        Crea y guarda una cita utilizando las reglas
        reales del modelo.
        """

        return Appointment.objects.create(
            patient=patient or self.patient,
            psychologist=(
                psychologist
                or self.psychologist
            ),
            availability_slot=slot,
            status=status,
            reason="Consulta de prueba",
            appointment_type=(
                Appointment.AppointmentType.IN_PERSON
            ),
            cancelled_reason=cancelled_reason,
        )

    def test_creating_pending_appointment_books_slot(self):
        """
        Una cita pendiente debe cambiar automáticamente
        el cupo de Disponible a Reservado.
        """

        slot = self.create_slot()

        appointment = self.create_appointment(
            slot=slot,
        )

        slot.refresh_from_db()

        self.assertEqual(
            appointment.status,
            Appointment.Status.PENDING,
        )

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.BOOKED,
        )

    def test_creating_confirmed_appointment_books_slot(self):
        """
        Una cita confirmada también debe mantener
        reservado su cupo.
        """

        slot = self.create_slot()

        self.create_appointment(
            slot=slot,
            status=Appointment.Status.CONFIRMED,
        )

        slot.refresh_from_db()

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.BOOKED,
        )

    def test_new_appointment_cannot_use_booked_slot(self):
        """
        Un cupo reservado no puede utilizarse para crear
        una segunda cita.
        """

        slot = self.create_slot()

        self.create_appointment(
            slot=slot,
        )

        slot.refresh_from_db()

        second_appointment = Appointment(
            patient=self.other_patient,
            psychologist=self.psychologist,
            availability_slot=slot,
            status=Appointment.Status.PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            second_appointment.save()

        self.assertIn(
            "availability_slot",
            context.exception.message_dict,
        )

        self.assertIn(
            (
                "Solo se pueden reservar cupos "
                "con estado Disponible."
            ),
            context.exception.message_dict[
                "availability_slot"
            ],
        )

        self.assertEqual(
            Appointment.objects.count(),
            1,
        )

    def test_slot_must_belong_to_selected_psychologist(self):
        """
        El psicólogo asignado a la cita debe ser
        el propietario del cupo.
        """

        slot = self.create_slot(
            psychologist=self.psychologist,
        )

        appointment = Appointment(
            patient=self.patient,
            psychologist=self.other_psychologist,
            availability_slot=slot,
            status=Appointment.Status.PENDING,
        )

        with self.assertRaises(ValidationError) as context:
            appointment.save()

        self.assertIn(
            "availability_slot",
            context.exception.message_dict,
        )

        self.assertIn(
            (
                "El cupo seleccionado no pertenece "
                "al psicólogo indicado."
            ),
            context.exception.message_dict[
                "availability_slot"
            ],
        )

        slot.refresh_from_db()

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.AVAILABLE,
        )

    def test_cancelling_appointment_requires_reason(self):
        """
        No debe permitirse cancelar una cita sin registrar
        el motivo correspondiente.
        """

        slot = self.create_slot()

        appointment = self.create_appointment(
            slot=slot,
        )

        appointment.status = Appointment.Status.CANCELLED
        appointment.cancelled_reason = ""

        with self.assertRaises(ValidationError) as context:
            appointment.save()

        self.assertIn(
            "cancelled_reason",
            context.exception.message_dict,
        )

        appointment.refresh_from_db()
        slot.refresh_from_db()

        self.assertEqual(
            appointment.status,
            Appointment.Status.PENDING,
        )

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.BOOKED,
        )

    def test_cancelling_appointment_releases_slot(self):
        """
        Una cita cancelada debe liberar nuevamente
        el cupo asociado.
        """

        slot = self.create_slot()

        appointment = self.create_appointment(
            slot=slot,
        )

        appointment.status = Appointment.Status.CANCELLED
        appointment.cancelled_reason = (
            "El paciente no podrá asistir."
        )
        appointment.save()

        appointment.refresh_from_db()
        slot.refresh_from_db()

        self.assertEqual(
            appointment.status,
            Appointment.Status.CANCELLED,
        )

        self.assertEqual(
            appointment.cancelled_reason,
            "El paciente no podrá asistir.",
        )

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.AVAILABLE,
        )

    def test_cancelled_slot_can_be_used_by_another_appointment(self):
        """
        Después de cancelar una cita, su cupo puede ser
        reservado nuevamente por otro paciente.
        """

        slot = self.create_slot()

        appointment = self.create_appointment(
            slot=slot,
        )

        appointment.status = Appointment.Status.CANCELLED
        appointment.cancelled_reason = (
            "Cancelación de prueba."
        )
        appointment.save()

        slot.refresh_from_db()

        new_appointment = self.create_appointment(
            slot=slot,
            patient=self.other_patient,
        )

        slot.refresh_from_db()

        self.assertEqual(
            new_appointment.status,
            Appointment.Status.PENDING,
        )

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.BOOKED,
        )

        self.assertEqual(
            Appointment.objects.count(),
            2,
        )

    def test_reprogramming_releases_old_slot_and_books_new_slot(
        self,
    ):
        """
        Al cambiar una cita de cupo, el anterior debe quedar
        disponible y el nuevo debe quedar reservado.
        """

        old_slot = self.create_slot(
            start_time=self.base_start_time,
        )

        new_slot = self.create_slot(
            start_time=(
                self.base_start_time
                + timedelta(hours=2)
            ),
        )

        appointment = self.create_appointment(
            slot=old_slot,
        )

        old_slot.refresh_from_db()
        new_slot.refresh_from_db()

        self.assertEqual(
            old_slot.status,
            AvailabilitySlot.Status.BOOKED,
        )

        self.assertEqual(
            new_slot.status,
            AvailabilitySlot.Status.AVAILABLE,
        )

        appointment.availability_slot = new_slot
        appointment.save()

        appointment.refresh_from_db()
        old_slot.refresh_from_db()
        new_slot.refresh_from_db()

        self.assertEqual(
            appointment.availability_slot,
            new_slot,
        )

        self.assertEqual(
            old_slot.status,
            AvailabilitySlot.Status.AVAILABLE,
        )

        self.assertEqual(
            new_slot.status,
            AvailabilitySlot.Status.BOOKED,
        )

    def test_completed_appointment_keeps_slot_booked(self):
        """
        Una cita completada debe conservar el cupo
        en estado Reservado.
        """

        slot = self.create_slot()

        appointment = self.create_appointment(
            slot=slot,
        )

        appointment.status = Appointment.Status.COMPLETED
        appointment.save()

        appointment.refresh_from_db()
        slot.refresh_from_db()

        self.assertEqual(
            appointment.status,
            Appointment.Status.COMPLETED,
        )

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.BOOKED,
        )

    def test_appointment_properties_return_expected_values(self):
        """
        Las propiedades auxiliares deben reflejar correctamente
        el tipo, duración y estado de la cita.
        """

        slot = self.create_slot(
            duration_minutes=90,
        )

        appointment = Appointment(
            patient=self.patient,
            psychologist=self.psychologist,
            availability_slot=slot,
            status=Appointment.Status.CONFIRMED,
            appointment_type=(
                Appointment.AppointmentType.VIRTUAL
            ),
        )

        self.assertEqual(
            appointment.duration,
            timedelta(minutes=90),
        )

        self.assertTrue(
            appointment.is_virtual,
        )

        self.assertTrue(
            appointment.is_active,
        )

        self.assertFalse(
            appointment.is_finished,
        )

        appointment.status = Appointment.Status.COMPLETED

        self.assertFalse(
            appointment.is_active,
        )

        self.assertTrue(
            appointment.is_finished,
        )