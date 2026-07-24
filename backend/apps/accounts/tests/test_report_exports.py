import csv
import io
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Account
from apps.appointments.models import Appointment


class AdminAppointmentCsvExportTests(TestCase):
    """
    Pruebas para la exportación administrativa de citas.

    Se verifica:
    - el tipo de respuesta;
    - el nombre del archivo;
    - los encabezados;
    - el contenido de las filas;
    - el motivo de cancelación;
    - el uso del período seleccionado;
    - la redirección cuando el período es inválido.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Crea la cuenta administradora utilizada
        por todas las pruebas.
        """

        cls.admin_account = Account(
            email="admin.csv@example.com",
            first_name="Admin",
            last_name="Reportes",
            role=Account.Role.ADMIN,
            is_active=True,
            is_staff=True,
        )

        cls.admin_account.set_password(
            "TestPassword123!",
        )

        cls.admin_account.save()

    def setUp(self):
        """
        Inicia sesión como administrador antes
        de cada prueba.
        """

        self.client.force_login(
            self.admin_account,
        )

    def build_account(
        self,
        *,
        first_name,
        last_name,
        email,
    ):
        """
        Construye un objeto sencillo que representa
        una cuenta relacionada con una cita.
        """

        return SimpleNamespace(
            first_name=first_name,
            last_name=last_name,
            email=email,
        )

    def build_appointment(
        self,
        *,
        start_time,
        end_time,
        status,
        cancelled_reason="",
    ):
        """
        Construye una cita simulada con las relaciones
        necesarias para generar el archivo CSV.
        """

        psychologist_account = self.build_account(
            first_name="Andrea",
            last_name="Psicóloga",
            email="andrea.psicologa@example.com",
        )

        patient_account = self.build_account(
            first_name="Carlos",
            last_name="Paciente",
            email="carlos.paciente@example.com",
        )

        psychologist = SimpleNamespace(
            account=psychologist_account,
        )

        patient = SimpleNamespace(
            account=patient_account,
        )

        availability_slot = SimpleNamespace(
            start_time=start_time,
            end_time=end_time,
        )

        status_labels = {
            Appointment.Status.PENDING: "Pendiente",
            Appointment.Status.CONFIRMED: "Confirmada",
            Appointment.Status.COMPLETED: "Completada",
            Appointment.Status.CANCELLED: "Cancelada",
        }

        appointment = SimpleNamespace(
            psychologist=psychologist,
            patient=patient,
            availability_slot=availability_slot,
            status=status,
            cancelled_reason=cancelled_reason,
        )

        appointment.get_status_display = Mock(
            return_value=status_labels[status],
        )

        return appointment

    def decode_csv_response(self, response):
        """
        Convierte el contenido de la respuesta CSV
        en una lista de filas.

        utf-8-sig elimina correctamente el marcador BOM
        agregado para facilitar la apertura en Excel.
        """

        decoded_content = response.content.decode(
            "utf-8-sig",
        )

        return list(
            csv.reader(
                io.StringIO(decoded_content),
            )
        )

    def full_history_period(self):
        """
        Devuelve la estructura correspondiente
        al historial completo.
        """

        return {
            "period_filter": "",
            "start_date": None,
            "end_date": None,
            "start_date_raw": "",
            "end_date_raw": "",
            "date_filter_error": "",
            "appointments_are_filtered": False,
            "period_summary": "Historial completo",
        }

    @patch(
        "apps.accounts.views.filter_appointments_by_period"
    )
    @patch(
        "apps.accounts.views.resolve_report_period"
    )
    def test_export_returns_csv_response(
        self,
        mocked_resolve_period,
        mocked_filter_appointments,
    ):
        """
        La exportación debe responder con un archivo CSV
        descargable.
        """

        mocked_resolve_period.return_value = (
            self.full_history_period()
        )

        mocked_filter_appointments.return_value = []

        response = self.client.get(
            reverse("admin-report-appointments-csv"),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTrue(
            response["Content-Type"].startswith(
                "text/csv",
            )
        )

        self.assertIn(
            "attachment;",
            response["Content-Disposition"],
        )

        self.assertIn(
            "reporte_citas_historial_completo.csv",
            response["Content-Disposition"],
        )

    @patch(
        "apps.accounts.views.filter_appointments_by_period"
    )
    @patch(
        "apps.accounts.views.resolve_report_period"
    )
    def test_export_contains_expected_headers(
        self,
        mocked_resolve_period,
        mocked_filter_appointments,
    ):
        """
        El archivo debe incluir todos los encabezados
        definidos para el reporte de citas.
        """

        mocked_resolve_period.return_value = (
            self.full_history_period()
        )

        mocked_filter_appointments.return_value = []

        response = self.client.get(
            reverse("admin-report-appointments-csv"),
        )

        rows = self.decode_csv_response(response)

        self.assertEqual(
            rows[0],
            [
                "Fecha",
                "Hora inicial",
                "Hora final",
                "Psicólogo",
                "Correo del psicólogo",
                "Paciente",
                "Correo del paciente",
                "Estado",
                "Motivo de cancelación",
            ],
        )

    @patch(
        "apps.accounts.views.filter_appointments_by_period"
    )
    @patch(
        "apps.accounts.views.resolve_report_period"
    )
    def test_export_contains_appointment_information(
        self,
        mocked_resolve_period,
        mocked_filter_appointments,
    ):
        """
        La exportación debe incluir correctamente
        los datos principales de una cita.
        """

        mocked_resolve_period.return_value = (
            self.full_history_period()
        )

        start_time = timezone.make_aware(
            datetime(
                2026,
                7,
                20,
                9,
                30,
            )
        )

        end_time = timezone.make_aware(
            datetime(
                2026,
                7,
                20,
                10,
                30,
            )
        )

        appointment = self.build_appointment(
            start_time=start_time,
            end_time=end_time,
            status=Appointment.Status.COMPLETED,
        )

        mocked_filter_appointments.return_value = [
            appointment,
        ]

        response = self.client.get(
            reverse("admin-report-appointments-csv"),
        )

        rows = self.decode_csv_response(response)

        self.assertEqual(
            len(rows),
            2,
        )

        exported_row = rows[1]

        self.assertEqual(
            exported_row[0],
            "20/07/2026",
        )

        self.assertEqual(
            exported_row[3],
            "Andrea Psicóloga",
        )

        self.assertEqual(
            exported_row[4],
            "andrea.psicologa@example.com",
        )

        self.assertEqual(
            exported_row[5],
            "Carlos Paciente",
        )

        self.assertEqual(
            exported_row[6],
            "carlos.paciente@example.com",
        )

        self.assertEqual(
            exported_row[7],
            "Completada",
        )

        self.assertEqual(
            exported_row[8],
            "",
        )

    @patch(
        "apps.accounts.views.filter_appointments_by_period"
    )
    @patch(
        "apps.accounts.views.resolve_report_period"
    )
    def test_export_includes_cancelled_reason(
        self,
        mocked_resolve_period,
        mocked_filter_appointments,
    ):
        """
        Una cita cancelada debe incluir su motivo
        de cancelación en la última columna.
        """

        mocked_resolve_period.return_value = (
            self.full_history_period()
        )

        start_time = timezone.make_aware(
            datetime(
                2026,
                7,
                21,
                14,
                0,
            )
        )

        end_time = timezone.make_aware(
            datetime(
                2026,
                7,
                21,
                15,
                0,
            )
        )

        appointment = self.build_appointment(
            start_time=start_time,
            end_time=end_time,
            status=Appointment.Status.CANCELLED,
            cancelled_reason=(
                "El paciente informó que no podría asistir."
            ),
        )

        mocked_filter_appointments.return_value = [
            appointment,
        ]

        response = self.client.get(
            reverse("admin-report-appointments-csv"),
        )

        rows = self.decode_csv_response(response)

        exported_row = rows[1]

        self.assertEqual(
            exported_row[7],
            "Cancelada",
        )

        self.assertEqual(
            exported_row[8],
            (
                "El paciente informó que no podría "
                "asistir."
            ),
        )

    @patch(
        "apps.accounts.views.filter_appointments_by_period"
    )
    @patch(
        "apps.accounts.views.resolve_report_period"
    )
    def test_export_uses_selected_date_range(
        self,
        mocked_resolve_period,
        mocked_filter_appointments,
    ):
        """
        La exportación debe enviar las fechas resueltas
        a la función encargada de filtrar las citas.
        """

        start_date = date(
            2026,
            7,
            10,
        )

        end_date = date(
            2026,
            7,
            20,
        )

        mocked_resolve_period.return_value = {
            "period_filter": "",
            "start_date": start_date,
            "end_date": end_date,
            "start_date_raw": "2026-07-10",
            "end_date_raw": "2026-07-20",
            "date_filter_error": "",
            "appointments_are_filtered": True,
            "period_summary": (
                "Del 10/07/2026 al 20/07/2026"
            ),
        }

        mocked_filter_appointments.return_value = []

        response = self.client.get(
            reverse("admin-report-appointments-csv"),
            data={
                "start_date": "2026-07-10",
                "end_date": "2026-07-20",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mocked_filter_appointments.assert_called_once()

        call_arguments = (
            mocked_filter_appointments.call_args.kwargs
        )

        self.assertEqual(
            call_arguments["start_date"],
            start_date,
        )

        self.assertEqual(
            call_arguments["end_date"],
            end_date,
        )

        self.assertIn(
            (
                "reporte_citas_2026-07-10"
                "_a_2026-07-20.csv"
            ),
            response["Content-Disposition"],
        )

    @patch(
        "apps.accounts.views.resolve_report_period"
    )
    def test_invalid_period_redirects_to_report_dashboard(
        self,
        mocked_resolve_period,
    ):
        """
        Cuando el período es inválido no debe generarse
        el archivo CSV.
        """

        mocked_resolve_period.return_value = {
            "period_filter": "",
            "start_date": date(2026, 7, 25),
            "end_date": date(2026, 7, 20),
            "start_date_raw": "2026-07-25",
            "end_date_raw": "2026-07-20",
            "date_filter_error": (
                "La fecha inicial no puede ser posterior "
                "a la fecha final."
            ),
            "appointments_are_filtered": True,
            "period_summary": "Historial completo",
        }

        response = self.client.get(
            reverse("admin-report-appointments-csv"),
            data={
                "start_date": "2026-07-25",
                "end_date": "2026-07-20",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse("admin-report-dashboard"),
        )