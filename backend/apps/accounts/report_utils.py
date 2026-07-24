from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_date


def resolve_report_period(request):
    """
    Obtiene y valida el período seleccionado para los reportes.

    Soporta:
    - Hoy.
    - Últimos 7 días.
    - Este mes.
    - Rango personalizado.
    - Historial completo.

    Retorna un diccionario con las fechas resueltas,
    los valores originales del formulario y cualquier
    error de validación.
    """

    period_filter = request.GET.get(
        "period",
        "",
    ).strip().lower()

    start_date_raw = request.GET.get(
        "start_date",
        "",
    ).strip()

    end_date_raw = request.GET.get(
        "end_date",
        "",
    ).strip()

    today = timezone.localdate()

    valid_periods = {
        "today",
        "last_7_days",
        "this_month",
    }

    if period_filter not in valid_periods:
        period_filter = ""

    if period_filter == "today":
        start_date = today
        end_date = today

        start_date_raw = start_date.isoformat()
        end_date_raw = end_date.isoformat()

    elif period_filter == "last_7_days":
        start_date = today - timedelta(days=6)
        end_date = today

        start_date_raw = start_date.isoformat()
        end_date_raw = end_date.isoformat()

    elif period_filter == "this_month":
        start_date = today.replace(day=1)
        end_date = today

        start_date_raw = start_date.isoformat()
        end_date_raw = end_date.isoformat()

    else:
        start_date = (
            parse_date(start_date_raw)
            if start_date_raw
            else None
        )

        end_date = (
            parse_date(end_date_raw)
            if end_date_raw
            else None
        )

    date_filter_error = ""

    if start_date_raw and start_date is None:
        date_filter_error = (
            "La fecha inicial no tiene un formato válido."
        )

    elif end_date_raw and end_date is None:
        date_filter_error = (
            "La fecha final no tiene un formato válido."
        )

    elif (
        start_date
        and end_date
        and start_date > end_date
    ):
        date_filter_error = (
            "La fecha inicial no puede ser posterior "
            "a la fecha final."
        )

    appointments_are_filtered = bool(
        start_date or end_date
    )

    period_summary = "Historial completo"

    if not date_filter_error:
        if start_date and end_date:
            period_summary = (
                f"Del {start_date.strftime('%d/%m/%Y')} "
                f"al {end_date.strftime('%d/%m/%Y')}"
            )

        elif start_date:
            period_summary = (
                f"Desde el {start_date.strftime('%d/%m/%Y')}"
            )

        elif end_date:
            period_summary = (
                f"Hasta el {end_date.strftime('%d/%m/%Y')}"
            )

    return {
        "period_filter": period_filter,
        "start_date": start_date,
        "end_date": end_date,
        "start_date_raw": start_date_raw,
        "end_date_raw": end_date_raw,
        "date_filter_error": date_filter_error,
        "appointments_are_filtered": (
            appointments_are_filtered
        ),
        "period_summary": period_summary,
    }


def filter_appointments_by_period(
    appointments,
    start_date=None,
    end_date=None,
):
    """
    Aplica el rango de fechas a un QuerySet de citas.

    La fecha utilizada corresponde al inicio del cupo
    asociado a la cita.
    """

    if start_date:
        appointments = appointments.filter(
            availability_slot__start_time__date__gte=(
                start_date
            ),
        )

    if end_date:
        appointments = appointments.filter(
            availability_slot__start_time__date__lte=(
                end_date
            ),
        )

    return appointments