from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Account
from apps.appointments.models import AvailabilitySlot
from apps.psychologists.models import Psychologist


class AvailabilitySlotModelTests(TestCase):
    """
    Pruebas para las reglas de negocio de AvailabilitySlot.

    Se comprueba:
    - que la hora final sea posterior a la inicial;
    - que no se creen cupos en el pasado;
    - que un psicólogo no tenga cupos solapados;
    - que se permitan cupos consecutivos;
    - que dos psicólogos puedan usar el mismo horario;
    - que al editar un cupo no se detecte a sí mismo
      como un horario solapado.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Crea las cuentas y perfiles reutilizados
        durante las pruebas.
        """

        cls.psychologist_account = cls.create_account(
            email="slot.psychologist@example.com",
            first_name="Laura",
            last_name="Psicóloga",
        )

        cls.other_psychologist_account = cls.create_account(
            email="other.slot.psychologist@example.com",
            first_name="Daniel",
            last_name="Psicólogo",
        )

        cls.psychologist = cls.create_profile(
            Psychologist,
            account=cls.psychologist_account,
        )

        cls.other_psychologist = cls.create_profile(
            Psychologist,
            account=cls.other_psychologist_account,
        )

        cls.base_start_time = timezone.make_aware(
            datetime(
                2030,
                8,
                10,
                8,
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
    ):
        """
        Crea una cuenta de psicólogo para las pruebas.
        """

        account = Account(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=Account.Role.PSYCHOLOGIST,
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
        los campos obligatorios del modelo.

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

    def build_slot(
        self,
        *,
        psychologist=None,
        start_time=None,
        end_time=None,
        status=AvailabilitySlot.Status.AVAILABLE,
    ):
        """
        Construye un cupo sin guardarlo todavía.
        """

        psychologist = (
            psychologist
            or self.psychologist
        )

        start_time = (
            start_time
            or self.base_start_time
        )

        end_time = (
            end_time
            or start_time + timedelta(hours=1)
        )

        return AvailabilitySlot(
            psychologist=psychologist,
            start_time=start_time,
            end_time=end_time,
            status=status,
        )

    def create_valid_slot(
        self,
        *,
        psychologist=None,
        start_time=None,
        end_time=None,
        status=AvailabilitySlot.Status.AVAILABLE,
    ):
        """
        Valida y guarda un cupo correcto.
        """

        slot = self.build_slot(
            psychologist=psychologist,
            start_time=start_time,
            end_time=end_time,
            status=status,
        )

        slot.full_clean()
        slot.save()

        return slot

    def test_end_time_must_be_after_start_time(self):
        """
        La fecha u hora final debe ser posterior
        a la fecha u hora inicial.
        """

        slot = self.build_slot(
            start_time=self.base_start_time,
            end_time=self.base_start_time,
        )

        with self.assertRaises(ValidationError) as context:
            slot.full_clean()

        self.assertIn(
            "end_time",
            context.exception.message_dict,
        )

        self.assertIn(
            (
                "La fecha u hora final debe ser posterior "
                "a la fecha u hora inicial."
            ),
            context.exception.message_dict["end_time"],
        )

    def test_end_time_cannot_be_before_start_time(self):
        """
        Tampoco debe aceptarse una hora final anterior
        a la hora inicial.
        """

        slot = self.build_slot(
            start_time=self.base_start_time,
            end_time=(
                self.base_start_time
                - timedelta(minutes=30)
            ),
        )

        with self.assertRaises(ValidationError) as context:
            slot.full_clean()

        self.assertIn(
            "end_time",
            context.exception.message_dict,
        )

    def test_new_slot_cannot_be_created_in_past(self):
        """
        No debe permitirse crear un nuevo cupo
        cuya hora de inicio ya pasó.
        """

        past_start_time = (
            timezone.now()
            - timedelta(days=1)
        )

        slot = self.build_slot(
            start_time=past_start_time,
            end_time=(
                past_start_time
                + timedelta(hours=1)
            ),
        )

        with self.assertRaises(ValidationError) as context:
            slot.full_clean()

        self.assertIn(
            "start_time",
            context.exception.message_dict,
        )

        self.assertIn(
            (
                "No se puede crear un cupo en una fecha "
                "u hora pasada."
            ),
            context.exception.message_dict["start_time"],
        )

    def test_valid_future_slot_can_be_created(self):
        """
        Un cupo futuro con un rango válido
        debe superar las validaciones.
        """

        slot = self.build_slot()

        slot.full_clean()
        slot.save()

        self.assertIsNotNone(slot.pk)

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.AVAILABLE,
        )

    def test_psychologist_cannot_have_overlapping_slots(self):
        """
        Un psicólogo no puede registrar dos cupos
        cuyos horarios se crucen.
        """

        self.create_valid_slot(
            start_time=self.base_start_time,
            end_time=(
                self.base_start_time
                + timedelta(hours=1)
            ),
        )

        overlapping_slot = self.build_slot(
            start_time=(
                self.base_start_time
                + timedelta(minutes=30)
            ),
            end_time=(
                self.base_start_time
                + timedelta(hours=1, minutes=30)
            ),
        )

        with self.assertRaises(ValidationError) as context:
            overlapping_slot.full_clean()

        self.assertIn(
            "start_time",
            context.exception.message_dict,
        )

        self.assertIn(
            (
                "Ya tienes un cupo que se cruza "
                "con el horario seleccionado."
            ),
            context.exception.message_dict["start_time"],
        )

    def test_slot_containing_existing_slot_is_rejected(self):
        """
        También debe detectarse el cruce cuando el nuevo cupo
        contiene completamente a otro cupo existente.
        """

        existing_start = (
            self.base_start_time
            + timedelta(hours=1)
        )

        existing_end = (
            existing_start
            + timedelta(hours=1)
        )

        self.create_valid_slot(
            start_time=existing_start,
            end_time=existing_end,
        )

        containing_slot = self.build_slot(
            start_time=self.base_start_time,
            end_time=(
                self.base_start_time
                + timedelta(hours=3)
            ),
        )

        with self.assertRaises(ValidationError):
            containing_slot.full_clean()

    def test_consecutive_slots_are_allowed(self):
        """
        Dos cupos consecutivos son válidos cuando el segundo
        comienza exactamente al finalizar el primero.
        """

        first_slot = self.create_valid_slot(
            start_time=self.base_start_time,
            end_time=(
                self.base_start_time
                + timedelta(hours=1)
            ),
        )

        second_slot = self.build_slot(
            start_time=first_slot.end_time,
            end_time=(
                first_slot.end_time
                + timedelta(hours=1)
            ),
        )

        second_slot.full_clean()
        second_slot.save()

        self.assertIsNotNone(second_slot.pk)

        self.assertEqual(
            AvailabilitySlot.objects.count(),
            2,
        )

    def test_different_psychologists_can_use_same_schedule(self):
        """
        Dos psicólogos distintos pueden crear cupos
        en el mismo rango de tiempo.
        """

        first_slot = self.create_valid_slot(
            psychologist=self.psychologist,
            start_time=self.base_start_time,
        )

        second_slot = self.build_slot(
            psychologist=self.other_psychologist,
            start_time=self.base_start_time,
        )

        second_slot.full_clean()
        second_slot.save()

        self.assertEqual(
            first_slot.start_time,
            second_slot.start_time,
        )

        self.assertNotEqual(
            first_slot.psychologist,
            second_slot.psychologist,
        )

        self.assertEqual(
            AvailabilitySlot.objects.count(),
            2,
        )

    def test_editing_slot_does_not_overlap_with_itself(self):
        """
        Al validar un cupo existente, debe excluirse
        a sí mismo de la consulta de solapamientos.
        """

        slot = self.create_valid_slot()

        slot.status = AvailabilitySlot.Status.BLOCKED

        slot.full_clean()
        slot.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        slot.refresh_from_db()

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.BLOCKED,
        )

    def test_editing_slot_to_overlapping_schedule_is_rejected(self):
        """
        Al editar un cupo, no debe permitirse moverlo
        a un horario ocupado por otro cupo.
        """

        first_slot = self.create_valid_slot(
            start_time=self.base_start_time,
            end_time=(
                self.base_start_time
                + timedelta(hours=1)
            ),
        )

        second_slot = self.create_valid_slot(
            start_time=(
                self.base_start_time
                + timedelta(hours=2)
            ),
            end_time=(
                self.base_start_time
                + timedelta(hours=3)
            ),
        )

        second_slot.start_time = (
            first_slot.start_time
            + timedelta(minutes=30)
        )

        second_slot.end_time = (
            first_slot.end_time
            + timedelta(minutes=30)
        )

        with self.assertRaises(ValidationError) as context:
            second_slot.full_clean()

        self.assertIn(
            "start_time",
            context.exception.message_dict,
        )

    def test_existing_historical_slot_can_be_edited(self):
        """
        La validación de fechas pasadas solo se aplica
        cuando el cupo todavía no existe.

        Un cupo histórico ya guardado puede modificarse
        sin ser rechazado por su fecha.
        """

        slot = AvailabilitySlot.objects.create(
            psychologist=self.psychologist,
            start_time=(
                timezone.now()
                - timedelta(days=2)
            ),
            end_time=(
                timezone.now()
                - timedelta(days=2)
                + timedelta(hours=1)
            ),
            status=AvailabilitySlot.Status.AVAILABLE,
        )

        slot.status = AvailabilitySlot.Status.CANCELLED

        slot.full_clean()
        slot.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        slot.refresh_from_db()

        self.assertEqual(
            slot.status,
            AvailabilitySlot.Status.CANCELLED,
        )