from datetime import date
from unittest.mock import Mock, patch

from django.test import RequestFactory, SimpleTestCase

from apps.accounts.report_utils import (
    filter_appointments_by_period,
    resolve_report_period,
)


class ResolveReportPeriodTests(SimpleTestCase):
    """
    Pruebas para la función resolve_report_period.

    Verifican que los accesos rápidos, los rangos personalizados
    y las validaciones de fecha se resuelvan correctamente.
    """

    def setUp(self):
        """
        Prepara una fábrica de solicitudes HTTP para cada prueba.
        """

        self.request_factory = RequestFactory()
        self.today = date(2026, 7, 23)

    def build_request(self, query_params=None):
        """
        Construye una solicitud GET con los parámetros indicados.
        """

        return self.request_factory.get(
            "/administracion/reportes/",
            data=query_params or {},
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_returns_full_history_when_no_filters_are_sent(
        self,
        mocked_localdate,
    ):
        """
        Sin parámetros debe devolver el historial completo.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request()

        result = resolve_report_period(request)

        self.assertEqual(result["period_filter"], "")
        self.assertIsNone(result["start_date"])
        self.assertIsNone(result["end_date"])
        self.assertEqual(result["start_date_raw"], "")
        self.assertEqual(result["end_date_raw"], "")
        self.assertEqual(result["date_filter_error"], "")
        self.assertFalse(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Historial completo",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_resolves_today_period(
        self,
        mocked_localdate,
    ):
        """
        El acceso rápido Hoy debe usar la fecha actual
        como inicio y final del período.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "period": "today",
            }
        )

        result = resolve_report_period(request)

        self.assertEqual(result["period_filter"], "today")
        self.assertEqual(result["start_date"], self.today)
        self.assertEqual(result["end_date"], self.today)
        self.assertEqual(
            result["start_date_raw"],
            "2026-07-23",
        )
        self.assertEqual(
            result["end_date_raw"],
            "2026-07-23",
        )
        self.assertEqual(result["date_filter_error"], "")
        self.assertTrue(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Del 23/07/2026 al 23/07/2026",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_resolves_last_seven_days_period(
        self,
        mocked_localdate,
    ):
        """
        Últimos 7 días debe incluir el día actual
        y los seis días anteriores.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "period": "last_7_days",
            }
        )

        result = resolve_report_period(request)

        self.assertEqual(
            result["period_filter"],
            "last_7_days",
        )
        self.assertEqual(
            result["start_date"],
            date(2026, 7, 17),
        )
        self.assertEqual(
            result["end_date"],
            date(2026, 7, 23),
        )
        self.assertEqual(
            result["start_date_raw"],
            "2026-07-17",
        )
        self.assertEqual(
            result["end_date_raw"],
            "2026-07-23",
        )
        self.assertTrue(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Del 17/07/2026 al 23/07/2026",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_resolves_current_month_period(
        self,
        mocked_localdate,
    ):
        """
        Este mes debe comenzar el primer día del mes actual
        y terminar en la fecha actual.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "period": "this_month",
            }
        )

        result = resolve_report_period(request)

        self.assertEqual(
            result["period_filter"],
            "this_month",
        )
        self.assertEqual(
            result["start_date"],
            date(2026, 7, 1),
        )
        self.assertEqual(
            result["end_date"],
            date(2026, 7, 23),
        )
        self.assertEqual(
            result["start_date_raw"],
            "2026-07-01",
        )
        self.assertEqual(
            result["end_date_raw"],
            "2026-07-23",
        )
        self.assertTrue(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Del 01/07/2026 al 23/07/2026",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_resolves_valid_custom_date_range(
        self,
        mocked_localdate,
    ):
        """
        Un rango personalizado válido debe conservar
        las fechas recibidas.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "start_date": "2026-07-10",
                "end_date": "2026-07-20",
            }
        )

        result = resolve_report_period(request)

        self.assertEqual(result["period_filter"], "")
        self.assertEqual(
            result["start_date"],
            date(2026, 7, 10),
        )
        self.assertEqual(
            result["end_date"],
            date(2026, 7, 20),
        )
        self.assertEqual(result["date_filter_error"], "")
        self.assertTrue(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Del 10/07/2026 al 20/07/2026",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_resolves_only_start_date(
        self,
        mocked_localdate,
    ):
        """
        Cuando solo existe fecha inicial, el período
        debe mostrarse como Desde.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "start_date": "2026-07-10",
            }
        )

        result = resolve_report_period(request)

        self.assertEqual(
            result["start_date"],
            date(2026, 7, 10),
        )
        self.assertIsNone(result["end_date"])
        self.assertEqual(result["date_filter_error"], "")
        self.assertTrue(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Desde el 10/07/2026",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_resolves_only_end_date(
        self,
        mocked_localdate,
    ):
        """
        Cuando solo existe fecha final, el período
        debe mostrarse como Hasta.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "end_date": "2026-07-20",
            }
        )

        result = resolve_report_period(request)

        self.assertIsNone(result["start_date"])
        self.assertEqual(
            result["end_date"],
            date(2026, 7, 20),
        )
        self.assertEqual(result["date_filter_error"], "")
        self.assertTrue(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Hasta el 20/07/2026",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_rejects_start_date_after_end_date(
        self,
        mocked_localdate,
    ):
        """
        La fecha inicial no puede ser posterior
        a la fecha final.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "start_date": "2026-07-25",
                "end_date": "2026-07-21",
            }
        )

        result = resolve_report_period(request)

        self.assertEqual(
            result["date_filter_error"],
            (
                "La fecha inicial no puede ser posterior "
                "a la fecha final."
            ),
        )
        self.assertTrue(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Historial completo",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_rejects_invalid_start_date_format(
        self,
        mocked_localdate,
    ):
        """
        Una fecha inicial inválida debe devolver
        un mensaje de validación.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "start_date": "fecha-invalida",
                "end_date": "2026-07-20",
            }
        )

        result = resolve_report_period(request)

        self.assertIsNone(result["start_date"])
        self.assertEqual(
            result["end_date"],
            date(2026, 7, 20),
        )
        self.assertEqual(
            result["date_filter_error"],
            "La fecha inicial no tiene un formato válido.",
        )
        self.assertTrue(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Historial completo",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_rejects_invalid_end_date_format(
        self,
        mocked_localdate,
    ):
        """
        Una fecha final inválida debe devolver
        un mensaje de validación.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "start_date": "2026-07-10",
                "end_date": "fecha-invalida",
            }
        )

        result = resolve_report_period(request)

        self.assertEqual(
            result["start_date"],
            date(2026, 7, 10),
        )
        self.assertIsNone(result["end_date"])
        self.assertEqual(
            result["date_filter_error"],
            "La fecha final no tiene un formato válido.",
        )
        self.assertTrue(result["appointments_are_filtered"])
        self.assertEqual(
            result["period_summary"],
            "Historial completo",
        )

    @patch(
        "apps.accounts.report_utils.timezone.localdate"
    )
    def test_ignores_unknown_quick_period(
        self,
        mocked_localdate,
    ):
        """
        Un acceso rápido desconocido debe tratarse
        como historial completo.
        """

        mocked_localdate.return_value = self.today

        request = self.build_request(
            {
                "period": "unknown_period",
            }
        )

        result = resolve_report_period(request)

        self.assertEqual(result["period_filter"], "")
        self.assertIsNone(result["start_date"])
        self.assertIsNone(result["end_date"])
        self.assertFalse(result["appointments_are_filtered"])
        self.assertEqual(result["date_filter_error"], "")
        self.assertEqual(
            result["period_summary"],
            "Historial completo",
        )


class FilterAppointmentsByPeriodTests(SimpleTestCase):
    """
    Pruebas para filter_appointments_by_period.

    Se utiliza un QuerySet simulado para confirmar que la
    función aplica correctamente los filtros esperados.
    """

    def setUp(self):
        """
        Define fechas reutilizadas por las pruebas.
        """

        self.start_date = date(2026, 7, 10)
        self.end_date = date(2026, 7, 20)

    def test_returns_same_queryset_without_dates(self):
        """
        Sin fechas no debe aplicar filtros al QuerySet.
        """

        appointments = Mock()

        result = filter_appointments_by_period(
            appointments=appointments,
        )

        self.assertIs(result, appointments)
        appointments.filter.assert_not_called()

    def test_filters_using_only_start_date(self):
        """
        Con fecha inicial debe incluir citas desde esa fecha.
        """

        appointments = Mock()
        filtered_appointments = Mock()

        appointments.filter.return_value = filtered_appointments

        result = filter_appointments_by_period(
            appointments=appointments,
            start_date=self.start_date,
        )

        appointments.filter.assert_called_once_with(
            availability_slot__start_time__date__gte=(
                self.start_date
            ),
        )

        self.assertIs(result, filtered_appointments)

    def test_filters_using_only_end_date(self):
        """
        Con fecha final debe incluir citas hasta esa fecha.
        """

        appointments = Mock()
        filtered_appointments = Mock()

        appointments.filter.return_value = filtered_appointments

        result = filter_appointments_by_period(
            appointments=appointments,
            end_date=self.end_date,
        )

        appointments.filter.assert_called_once_with(
            availability_slot__start_time__date__lte=(
                self.end_date
            ),
        )

        self.assertIs(result, filtered_appointments)

    def test_filters_using_start_and_end_dates(self):
        """
        Cuando se reciben ambas fechas deben aplicarse
        los dos filtros de forma encadenada.
        """

        appointments = Mock()
        appointments_after_start_filter = Mock()
        appointments_after_end_filter = Mock()

        appointments.filter.return_value = (
            appointments_after_start_filter
        )

        appointments_after_start_filter.filter.return_value = (
            appointments_after_end_filter
        )

        result = filter_appointments_by_period(
            appointments=appointments,
            start_date=self.start_date,
            end_date=self.end_date,
        )

        appointments.filter.assert_called_once_with(
            availability_slot__start_time__date__gte=(
                self.start_date
            ),
        )

        appointments_after_start_filter.filter.assert_called_once_with(
            availability_slot__start_time__date__lte=(
                self.end_date
            ),
        )

        self.assertIs(
            result,
            appointments_after_end_filter,
        )

    def test_applies_filters_in_expected_order(self):
        """
        La fecha inicial debe aplicarse sobre el QuerySet original
        y la fecha final sobre el resultado del primer filtro.
        """

        appointments = Mock()
        appointments_after_start_filter = Mock()
        appointments_after_end_filter = Mock()

        appointments.filter.return_value = (
            appointments_after_start_filter
        )

        appointments_after_start_filter.filter.return_value = (
            appointments_after_end_filter
        )

        result = filter_appointments_by_period(
            appointments=appointments,
            start_date=self.start_date,
            end_date=self.end_date,
        )

        # El primer filtro se aplica sobre el QuerySet original.
        appointments.filter.assert_called_once_with(
            availability_slot__start_time__date__gte=(
                self.start_date
            ),
        )

        # El segundo filtro se aplica sobre el resultado
        # producido por el primer filtro.
        appointments_after_start_filter.filter.assert_called_once_with(
            availability_slot__start_time__date__lte=(
                self.end_date
            ),
        )

        self.assertIs(
            result,
            appointments_after_end_filter,
        )