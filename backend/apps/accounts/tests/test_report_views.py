from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Account


class AdminReportViewPermissionTests(TestCase):
    """
    Pruebas de acceso para el panel administrativo de reportes.

    Verifican que:
    - un administrador pueda consultar el reporte;
    - un psicólogo no pueda acceder;
    - un paciente no pueda acceder;
    - un usuario sin autenticación sea enviado al login.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Crea las cuentas que serán reutilizadas por todas
        las pruebas de esta clase.
        """

        cls.admin_account = cls.create_account(
            email="admin.reportes@example.com",
            first_name="Administrador",
            last_name="Reportes",
            role=Account.Role.ADMIN,
            is_staff=True,
        )

        cls.psychologist_account = cls.create_account(
            email="psicologo.reportes@example.com",
            first_name="Laura",
            last_name="Psicóloga",
            role=Account.Role.PSYCHOLOGIST,
        )

        cls.patient_account = cls.create_account(
            email="paciente.reportes@example.com",
            first_name="Carlos",
            last_name="Paciente",
            role=Account.Role.PATIENT,
        )

    @classmethod
    def create_account(
        cls,
        *,
        email,
        first_name,
        last_name,
        role,
        is_staff=False,
    ):
        """
        Crea una cuenta válida para utilizarla en las pruebas.

        Se construye directamente el modelo para no depender
        de la firma particular del administrador de usuarios.
        """

        account = Account(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
            is_staff=is_staff,
        )

        account.set_password("TestPassword123!")
        account.save()

        return account

    def test_anonymous_user_is_redirected_to_login(self):
        """
        Una persona sin sesión iniciada no puede acceder
        al panel de reportes.
        """

        response = self.client.get(
            reverse("admin-report-dashboard"),
        )

        self.assertEqual(response.status_code, 302)

        expected_login_url = (
            f"{reverse('login')}"
            f"?next={reverse('admin-report-dashboard')}"
        )

        self.assertEqual(
            response.url,
            expected_login_url,
        )

    def test_admin_can_access_report_dashboard(self):
        """
        El administrador puede abrir correctamente
        la pantalla principal de reportes.
        """

        self.client.force_login(
            self.admin_account,
        )

        response = self.client.get(
            reverse("admin-report-dashboard"),
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "accounts/admin_report_dashboard.html",
        )

        self.assertEqual(
            response.context["page_title"],
            "Reportes",
        )

    def test_psychologist_is_redirected_from_report_dashboard(self):
        """
        Un psicólogo no puede consultar el reporte administrativo.
        """

        self.client.force_login(
            self.psychologist_account,
        )

        response = self.client.get(
            reverse("admin-report-dashboard"),
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            response.url,
            reverse("dashboard-redirect"),
        )

    def test_patient_is_redirected_from_report_dashboard(self):
        """
        Un paciente no puede consultar el reporte administrativo.
        """

        self.client.force_login(
            self.patient_account,
        )

        response = self.client.get(
            reverse("admin-report-dashboard"),
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            response.url,
            reverse("dashboard-redirect"),
        )


class AdminReportDashboardResponseTests(TestCase):
    """
    Pruebas sobre el contenido básico enviado por
    la vista del panel administrativo de reportes.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin_account = Account(
            email="admin.contexto@example.com",
            first_name="Admin",
            last_name="Contexto",
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
        de cada prueba de esta clase.
        """

        self.client.force_login(
            self.admin_account,
        )

    def test_report_dashboard_returns_general_context(self):
        """
        La vista debe enviar los indicadores y filtros
        necesarios para construir el reporte.
        """

        response = self.client.get(
            reverse("admin-report-dashboard"),
        )

        self.assertEqual(response.status_code, 200)

        expected_context_variables = [
            "total_psychologists",
            "active_psychologist_accounts",
            "total_patients",
            "active_patient_accounts",
            "total_appointments",
            "pending_appointments",
            "confirmed_appointments",
            "completed_appointments",
            "cancelled_appointments",
            "pending_percentage",
            "completed_percentage",
            "cancelled_percentage",
            "chart_labels",
            "chart_values",
            "psychologists_report",
            "period_filter",
            "start_date",
            "end_date",
            "date_filter_error",
            "appointments_are_filtered",
            "period_summary",
        ]

        for variable_name in expected_context_variables:
            with self.subTest(
                variable_name=variable_name,
            ):
                self.assertIn(
                    variable_name,
                    response.context,
                )

    def test_report_dashboard_uses_full_history_by_default(self):
        """
        Sin parámetros de fecha debe mostrarse
        el historial completo.
        """

        response = self.client.get(
            reverse("admin-report-dashboard"),
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["period_filter"],
            "",
        )

        self.assertEqual(
            response.context["start_date"],
            "",
        )

        self.assertEqual(
            response.context["end_date"],
            "",
        )

        self.assertEqual(
            response.context["date_filter_error"],
            "",
        )

        self.assertFalse(
            response.context["appointments_are_filtered"],
        )

        self.assertEqual(
            response.context["period_summary"],
            "Historial completo",
        )

    def test_report_dashboard_accepts_custom_date_range(self):
        """
        Un rango manual válido debe conservarse
        dentro del contexto del reporte.
        """

        response = self.client.get(
            reverse("admin-report-dashboard"),
            data={
                "start_date": "2026-07-10",
                "end_date": "2026-07-20",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["start_date"],
            "2026-07-10",
        )

        self.assertEqual(
            response.context["end_date"],
            "2026-07-20",
        )

        self.assertEqual(
            response.context["date_filter_error"],
            "",
        )

        self.assertTrue(
            response.context["appointments_are_filtered"],
        )

        self.assertEqual(
            response.context["period_summary"],
            "Del 10/07/2026 al 20/07/2026",
        )

    def test_report_dashboard_shows_error_for_inverted_range(self):
        """
        La pantalla debe informar cuando la fecha inicial
        es posterior a la fecha final.
        """

        response = self.client.get(
            reverse("admin-report-dashboard"),
            data={
                "start_date": "2026-07-25",
                "end_date": "2026-07-20",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.context["date_filter_error"],
            (
                "La fecha inicial no puede ser posterior "
                "a la fecha final."
            ),
        )

        self.assertEqual(
            response.context["period_summary"],
            "Historial completo",
        )


class AdminReportExportPermissionTests(TestCase):
    """
    Pruebas de permisos para las dos exportaciones CSV.
    """

    @classmethod
    def setUpTestData(cls):
        cls.admin_account = cls.create_account(
            email="admin.exportaciones@example.com",
            role=Account.Role.ADMIN,
            is_staff=True,
        )

        cls.psychologist_account = cls.create_account(
            email="psicologo.exportaciones@example.com",
            role=Account.Role.PSYCHOLOGIST,
        )

        cls.patient_account = cls.create_account(
            email="paciente.exportaciones@example.com",
            role=Account.Role.PATIENT,
        )

    @classmethod
    def create_account(
        cls,
        *,
        email,
        role,
        is_staff=False,
    ):
        """
        Crea una cuenta reutilizable para las pruebas
        de permisos de exportación.
        """

        account = Account(
            email=email,
            first_name="Usuario",
            last_name="Prueba",
            role=role,
            is_active=True,
            is_staff=is_staff,
        )

        account.set_password("TestPassword123!")
        account.save()

        return account

    def test_admin_can_export_appointments_csv(self):
        """
        El administrador puede descargar el detalle de citas.
        """

        self.client.force_login(
            self.admin_account,
        )

        response = self.client.get(
            reverse("admin-report-appointments-csv"),
        )

        self.assertEqual(response.status_code, 200)

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

    def test_admin_can_export_psychologists_csv(self):
        """
        El administrador puede descargar el resumen
        de actividad por psicólogo.
        """

        self.client.force_login(
            self.admin_account,
        )

        response = self.client.get(
            reverse("admin-report-psychologists-csv"),
        )

        self.assertEqual(response.status_code, 200)

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

    def test_psychologist_cannot_export_appointments_csv(self):
        """
        Un psicólogo no puede descargar el reporte
        administrativo de citas.
        """

        self.client.force_login(
            self.psychologist_account,
        )

        response = self.client.get(
            reverse("admin-report-appointments-csv"),
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            response.url,
            reverse("dashboard-redirect"),
        )

    def test_patient_cannot_export_appointments_csv(self):
        """
        Un paciente no puede descargar el reporte
        administrativo de citas.
        """

        self.client.force_login(
            self.patient_account,
        )

        response = self.client.get(
            reverse("admin-report-appointments-csv"),
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            response.url,
            reverse("dashboard-redirect"),
        )

    def test_psychologist_cannot_export_psychologists_csv(self):
        """
        Un psicólogo no puede descargar el resumen
        administrativo por profesional.
        """

        self.client.force_login(
            self.psychologist_account,
        )

        response = self.client.get(
            reverse("admin-report-psychologists-csv"),
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            response.url,
            reverse("dashboard-redirect"),
        )

    def test_patient_cannot_export_psychologists_csv(self):
        """
        Un paciente no puede descargar el resumen
        administrativo por profesional.
        """

        self.client.force_login(
            self.patient_account,
        )

        response = self.client.get(
            reverse("admin-report-psychologists-csv"),
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            response.url,
            reverse("dashboard-redirect"),
        )