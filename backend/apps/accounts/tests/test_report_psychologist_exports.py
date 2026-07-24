import csv
import io
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Account


class AdminPsychologistCsvExportTests(TestCase):
    """
    Pruebas para la exportación administrativa
    del resumen de actividad por psicólogo.

    Se verifica:
    - el tipo de respuesta;
    - el nombre del archivo;
    - los encabezados;
    - los datos del psicólogo;
    - el estado de la cuenta;
    - los conteos del período;
    - el uso del rango seleccionado;
    - la redirección ante períodos inválidos.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Crea la cuenta administradora utilizada
        durante las pruebas.
        """

        cls.admin_account = Account(
            email="admin.psychologist.csv@example.com",
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
        de ejecutar cada prueba.
        """

        self.client.force_login(
            self.admin_account,
        )

    def full_history_period(self):
        """
        Devuelve el período correspondiente
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

    def build_psychologist(
        self,
        *,
        first_name="Andrea",
        last_name="Psicóloga",
        email="andrea.psicologa@example.com",
        is_active=True,
        total=10,
        pending=2,
        confirmed=1,
        completed=6,
        cancelled=1,
        patients_attended=4,
    ):
        """
        Construye un psicólogo simulado con los atributos
        calculados que utiliza la exportación.
        """

        account = SimpleNamespace(
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_active=is_active,
        )

        return SimpleNamespace(
            account=account,
            total_appointments_report=total,
            pending_appointments_report=pending,
            confirmed_appointments_report=confirmed,
            completed_appointments_report=completed,
            cancelled_appointments_report=cancelled,
            patients_attended_report=patients_attended,
        )

    def decode_csv_response(self, response):
        """
        Convierte el contenido CSV de la respuesta
        en una lista de filas.

        utf-8-sig elimina el marcador BOM utilizado
        para compatibilidad con Excel.
        """

        decoded_content = response.content.decode(
            "utf-8-sig",
        )

        return list(
            csv.reader(
                io.StringIO(decoded_content),
            )
        )

    def build_mocked_psychologist_queryset(
        self,
        psychologists,
    ):
        """
        Construye un QuerySet simulado que permite encadenar:

        select_related()
        annotate()
        order_by()
        """

        queryset = Mock()

        queryset.select_related.return_value = queryset
        queryset.annotate.return_value = queryset
        queryset.order_by.return_value = psychologists

        return queryset

    @patch(
        "apps.accounts.views.Psychologist.objects"
    )
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
        mocked_psychologist_objects,
    ):
        """
        La exportación debe responder con un archivo CSV
        descargable.
        """

        mocked_resolve_period.return_value = (
            self.full_history_period()
        )

        filtered_appointments = Mock()
        filtered_appointments.values.return_value = []

        mocked_filter_appointments.return_value = (
            filtered_appointments
        )

        psychologists_queryset = (
            self.build_mocked_psychologist_queryset([])
        )

        mocked_psychologist_objects.select_related.return_value = (
            psychologists_queryset
        )

        response = self.client.get(
            reverse("admin-report-psychologists-csv"),
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
            "reporte_psicologos_historial_completo.csv",
            response["Content-Disposition"],
        )

    @patch(
        "apps.accounts.views.Psychologist.objects"
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
        mocked_psychologist_objects,
    ):
        """
        El archivo debe incluir todos los encabezados
        definidos para el resumen por psicólogo.
        """

        mocked_resolve_period.return_value = (
            self.full_history_period()
        )

        filtered_appointments = Mock()
        filtered_appointments.values.return_value = []

        mocked_filter_appointments.return_value = (
            filtered_appointments
        )

        psychologists_queryset = (
            self.build_mocked_psychologist_queryset([])
        )

        mocked_psychologist_objects.select_related.return_value = (
            psychologists_queryset
        )

        response = self.client.get(
            reverse("admin-report-psychologists-csv"),
        )

        rows = self.decode_csv_response(response)

        self.assertEqual(
            rows[0],
            [
                "Psicólogo",
                "Correo",
                "Estado de la cuenta",
                "Total de citas",
                "Pendientes",
                "Confirmadas",
                "Completadas",
                "Canceladas",
                "Pacientes atendidos",
            ],
        )

    @patch(
        "apps.accounts.views.Psychologist.objects"
    )
    @patch(
        "apps.accounts.views.filter_appointments_by_period"
    )
    @patch(
        "apps.accounts.views.resolve_report_period"
    )
    def test_export_contains_psychologist_information(
        self,
        mocked_resolve_period,
        mocked_filter_appointments,
        mocked_psychologist_objects,
    ):
        """
        La exportación debe incluir el nombre, correo,
        estado y conteos del psicólogo.
        """

        mocked_resolve_period.return_value = (
            self.full_history_period()
        )

        filtered_appointments = Mock()
        filtered_appointments.values.return_value = []

        mocked_filter_appointments.return_value = (
            filtered_appointments
        )

        psychologist = self.build_psychologist(
            total=15,
            pending=2,
            confirmed=1,
            completed=9,
            cancelled=3,
            patients_attended=7,
        )

        psychologists_queryset = (
            self.build_mocked_psychologist_queryset(
                [psychologist]
            )
        )

        mocked_psychologist_objects.select_related.return_value = (
            psychologists_queryset
        )

        response = self.client.get(
            reverse("admin-report-psychologists-csv"),
        )

        rows = self.decode_csv_response(response)

        self.assertEqual(
            len(rows),
            2,
        )

        exported_row = rows[1]

        self.assertEqual(
            exported_row,
            [
                "Andrea Psicóloga",
                "andrea.psicologa@example.com",
                "Activa",
                "15",
                "2",
                "1",
                "9",
                "3",
                "7",
            ],
        )

    @patch(
        "apps.accounts.views.Psychologist.objects"
    )
    @patch(
        "apps.accounts.views.filter_appointments_by_period"
    )
    @patch(
        "apps.accounts.views.resolve_report_period"
    )
    def test_export_marks_inactive_account(
        self,
        mocked_resolve_period,
        mocked_filter_appointments,
        mocked_psychologist_objects,
    ):
        """
        Una cuenta desactivada debe aparecer como Inactiva.
        """

        mocked_resolve_period.return_value = (
            self.full_history_period()
        )

        filtered_appointments = Mock()
        filtered_appointments.values.return_value = []

        mocked_filter_appointments.return_value = (
            filtered_appointments
        )

        psychologist = self.build_psychologist(
            is_active=False,
        )

        psychologists_queryset = (
            self.build_mocked_psychologist_queryset(
                [psychologist]
            )
        )

        mocked_psychologist_objects.select_related.return_value = (
            psychologists_queryset
        )

        response = self.client.get(
            reverse("admin-report-psychologists-csv"),
        )

        rows = self.decode_csv_response(response)

        self.assertEqual(
            rows[1][2],
            "Inactiva",
        )

    @patch(
        "apps.accounts.views.Psychologist.objects"
    )
    @patch(
        "apps.accounts.views.filter_appointments_by_period"
    )
    @patch(
        "apps.accounts.views.resolve_report_period"
    )
    def test_export_uses_email_when_name_is_empty(
        self,
        mocked_resolve_period,
        mocked_filter_appointments,
        mocked_psychologist_objects,
    ):
        """
        Cuando el psicólogo no tiene nombre registrado,
        se debe utilizar su correo.
        """

        mocked_resolve_period.return_value = (
            self.full_history_period()
        )

        filtered_appointments = Mock()
        filtered_appointments.values.return_value = []

        mocked_filter_appointments.return_value = (
            filtered_appointments
        )

        psychologist = self.build_psychologist(
            first_name="",
            last_name="",
            email="sin.nombre@example.com",
        )

        psychologists_queryset = (
            self.build_mocked_psychologist_queryset(
                [psychologist]
            )
        )

        mocked_psychologist_objects.select_related.return_value = (
            psychologists_queryset
        )

        response = self.client.get(
            reverse("admin-report-psychologists-csv"),
        )

        rows = self.decode_csv_response(response)

        self.assertEqual(
            rows[1][0],
            "sin.nombre@example.com",
        )

    @patch(
        "apps.accounts.views.Psychologist.objects"
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
        mocked_psychologist_objects,
    ):
        """
        La exportación debe aplicar las fechas resueltas
        y reflejarlas en el nombre del archivo.
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

        filtered_appointments = Mock()
        filtered_appointments.values.return_value = []

        mocked_filter_appointments.return_value = (
            filtered_appointments
        )

        psychologists_queryset = (
            self.build_mocked_psychologist_queryset([])
        )

        mocked_psychologist_objects.select_related.return_value = (
            psychologists_queryset
        )

        response = self.client.get(
            reverse("admin-report-psychologists-csv"),
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
                "reporte_psicologos_2026-07-10"
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
        Un período inválido no debe generar
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
            reverse("admin-report-psychologists-csv"),
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