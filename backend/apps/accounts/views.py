import csv

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts.models import Account
from apps.accounts.report_utils import (
    filter_appointments_by_period,
    resolve_report_period,
)
from apps.appointments.models import Appointment
from apps.assignments.models import Assignment
from apps.patients.models import Patient
from apps.psychologists.models import Psychologist


@login_required
def dashboard_redirect(request):
    """
    Redirige al usuario autenticado hacia el dashboard
    correspondiente según el rol almacenado en su cuenta.
    """

    user = request.user

    if user.role == "ADMIN":
        return redirect("admin-dashboard")

    if user.role == "PSYCHOLOGIST":
        return redirect("psychologist-dashboard")

    if user.role == "PATIENT":
        return redirect("patient-dashboard")

    # Si la cuenta no tiene un rol válido, se cierra el flujo
    # enviando nuevamente al inicio de sesión.
    return redirect("login")


@login_required
def admin_dashboard(request):
    """
    Muestra el panel principal del administrador con un resumen
    de las cuentas registradas en el sistema.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    accounts = Account.objects.all()

    total_users = accounts.count()
    total_appointments = Appointment.objects.count()

    active_psychologists = accounts.filter(
        role=Account.Role.PSYCHOLOGIST,
        is_active=True,
    ).count()

    active_patients = accounts.filter(
        role=Account.Role.PATIENT,
        is_active=True,
    ).count()

    inactive_accounts = accounts.filter(
        is_active=False,
    ).count()

    context = {
        "page_title": "Panel de administración",
        "total_users": total_users,
        "total_appointments": total_appointments,
        "active_psychologists": active_psychologists,
        "active_patients": active_patients,
        "inactive_accounts": inactive_accounts,
    }

    return render(
        request,
        "dashboard/admin_dashboard.html",
        context,
    )


@login_required
def psychologist_dashboard(request):
    """
    Muestra el dashboard exclusivo para psicólogos
    utilizando información real de sus citas.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    psychologist = (
        Psychologist.objects
        .select_related("account")
        .get(account=request.user)
    )

    if psychologist.gender == Psychologist.Gender.FEMALE:
        welcome_text = "Bienvenida"

    elif psychologist.gender == Psychologist.Gender.MALE:
        welcome_text = "Bienvenido"

    else:
        welcome_text = "Te damos la bienvenida"

    now = timezone.now()
    today = timezone.localdate()

    appointments = (
        Appointment.objects
        .filter(
            psychologist__account=request.user,
        )
        .select_related(
            "patient",
            "patient__account",
            "psychologist",
            "availability_slot",
        )
    )

    # Próxima cita pendiente o confirmada.
    next_appointment = (
        appointments
        .filter(
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.CONFIRMED,
            ],
            availability_slot__start_time__gte=now,
        )
        .order_by(
            "availability_slot__start_time",
        )
        .first()
    )

    # Citas activas programadas para el día actual.
    today_appointments = (
        appointments
        .filter(
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.CONFIRMED,
            ],
            availability_slot__start_time__date=today,
            availability_slot__start_time__gte=now,
        )
        .order_by(
            "availability_slot__start_time",
        )
    )

    # Cantidad de pacientes distintos atendidos
    # en citas completadas.
    attended_patients_count = (
        appointments
        .filter(
            status=Appointment.Status.COMPLETED,
        )
        .values(
            "patient_id",
        )
        .distinct()
        .count()
    )

    # Asignaciones activas relacionadas con pacientes
    # atendidos por el psicólogo autenticado.
    active_assignments = (
        Assignment.objects
        .filter(
            session_note__appointment__psychologist__account=(
                request.user
            ),
            is_visible=True,
            status__in=[
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
            ],
        )
        .select_related(
            "session_note",
            "session_note__appointment",
            "session_note__clinical_record",
            "session_note__clinical_record__patient",
            "session_note__clinical_record__patient__account",
        )
        .order_by("-updated_at")
    )

    active_assignments_count = active_assignments.count()
    latest_active_assignment = active_assignments.first()

    context = {
        "page_title": "Panel del psicólogo",
        "next_appointment": next_appointment,
        "psychologist": psychologist,
        "welcome_text": welcome_text,
        "today_appointments": today_appointments,
        "today_appointments_count": today_appointments.count(),
        "attended_patients_count": attended_patients_count,
        "active_assignments_count": active_assignments_count,
        "latest_active_assignment": latest_active_assignment,
    }

    return render(
        request,
        "dashboard/psychologist_dashboard.html",
        context,
    )


@login_required
def patient_dashboard(request):
    """
    Muestra el dashboard exclusivo para pacientes
    utilizando información real de sus citas.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    patient = (
        Patient.objects
        .select_related("account")
        .get(account=request.user)
    )

    if patient.gender == Patient.Gender.FEMALE:
        welcome_text = "Bienvenida"

    else:
        welcome_text = "Bienvenido"

    now = timezone.now()

    appointments = (
        Appointment.objects
        .filter(
            patient__account=request.user,
        )
        .select_related(
            "psychologist",
            "psychologist__account",
            "availability_slot",
        )
    )

    # Próxima cita pendiente o confirmada cuya fecha
    # todavía no ha pasado.
    next_appointment = (
        appointments
        .filter(
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.CONFIRMED,
            ],
            availability_slot__start_time__gte=now,
        )
        .order_by(
            "availability_slot__start_time",
        )
        .first()
    )

    # Total de sesiones que ya fueron completadas.
    completed_appointments_count = (
        appointments
        .filter(
            status=Appointment.Status.COMPLETED,
        )
        .count()
    )

    active_assignments = (
        Assignment.objects
        .filter(
            session_note__clinical_record__patient__account=(
                request.user
            ),
            is_visible=True,
            status__in=[
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
            ],
        )
        .select_related(
            "session_note",
            "session_note__appointment",
            "session_note__appointment__psychologist",
            "session_note__appointment__psychologist__account",
        )
        .order_by("-created_at")
    )

    active_assignments_count = active_assignments.count()
    latest_active_assignment = active_assignments.first()

    context = {
        "page_title": "Panel del paciente",
        "welcome_text": welcome_text,
        "next_appointment": next_appointment,
        "completed_appointments_count": (
            completed_appointments_count
        ),
        "active_assignments_count": active_assignments_count,
        "latest_active_assignment": latest_active_assignment,
    }

    return render(
        request,
        "dashboard/patient_dashboard.html",
        context,
    )


@login_required
def profile_view(request):
    """
    Muestra la información básica de la cuenta
    del usuario autenticado.
    """

    context = {
        "page_title": "Mi perfil",
    }

    return render(
        request,
        "accounts/profile.html",
        context,
    )


@login_required
def admin_user_list(request):
    """
    Muestra todas las cuentas registradas en el sistema.

    El administrador puede:
    - buscar por nombre, apellido o correo;
    - filtrar por rol;
    - filtrar por estado de la cuenta;
    - consultar los resultados con paginación.

    Esta vista no muestra información clínica ni profesional.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    query = request.GET.get(
        "q",
        "",
    ).strip()

    role_filter = request.GET.get(
        "role",
        "",
    ).strip().upper()

    account_status = request.GET.get(
        "account_status",
        "",
    ).strip().lower()

    users = Account.objects.select_related(
        "psychologist_profile",
        "patient_profile",
    )

    if query:
        users = users.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    valid_roles = {
        Account.Role.ADMIN,
        Account.Role.PSYCHOLOGIST,
        Account.Role.PATIENT,
    }

    if role_filter in valid_roles:
        users = users.filter(
            role=role_filter,
        )

    else:
        role_filter = ""

    if account_status == "active":
        users = users.filter(
            is_active=True,
        )

    elif account_status == "inactive":
        users = users.filter(
            is_active=False,
        )

    else:
        account_status = ""

    users = users.order_by(
        "first_name",
        "last_name",
        "email",
    )

    filtered_users_count = users.count()

    paginator = Paginator(
        users,
        10,
    )

    page_obj = paginator.get_page(
        request.GET.get("page"),
    )

    context = {
        "page_title": "Usuarios",
        "page_obj": page_obj,
        "query": query,
        "role_filter": role_filter,
        "account_status": account_status,
        "filtered_users_count": filtered_users_count,
        "role_choices": Account.Role.choices,
    }

    return render(
        request,
        "accounts/admin_user_list.html",
        context,
    )


@login_required
def admin_report_dashboard(request):
    """
    Muestra indicadores administrativos generales del sistema.

    Los indicadores de psicólogos y pacientes son acumulados.
    Los indicadores de citas pueden filtrarse por rango de fechas.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    # ==========================================
    # Cuentas y perfiles
    # ==========================================

    total_psychologists = Psychologist.objects.count()
    total_patients = Patient.objects.count()

    active_psychologist_accounts = (
        Psychologist.objects
        .filter(
            account__is_active=True,
        )
        .count()
    )

    active_patient_accounts = (
        Patient.objects
        .filter(
            account__is_active=True,
        )
        .count()
    )

    # ==========================================
    # Resolver el período del reporte
    # ==========================================

    report_period = resolve_report_period(request)

    period_filter = report_period["period_filter"]
    start_date = report_period["start_date"]
    end_date = report_period["end_date"]
    start_date_raw = report_period["start_date_raw"]
    end_date_raw = report_period["end_date_raw"]
    date_filter_error = report_period["date_filter_error"]
    appointments_are_filtered = report_period[
        "appointments_are_filtered"
    ]
    period_summary = report_period["period_summary"]

    # ==========================================
    # Consultar las citas del período
    # ==========================================

    appointments = Appointment.objects.all()

    # Solo se aplica el período cuando no existen
    # errores de validación en las fechas.
    if not date_filter_error:
        appointments = filter_appointments_by_period(
            appointments=appointments,
            start_date=start_date,
            end_date=end_date,
        )

    # ==========================================
    # Citas agrupadas por estado
    # ==========================================

    total_appointments = appointments.count()

    pending_appointments = appointments.filter(
        status=Appointment.Status.PENDING,
    ).count()

    confirmed_appointments = appointments.filter(
        status=Appointment.Status.CONFIRMED,
    ).count()

    completed_appointments = appointments.filter(
        status=Appointment.Status.COMPLETED,
    ).count()

    cancelled_appointments = appointments.filter(
        status=Appointment.Status.CANCELLED,
    ).count()

    # ==========================================
    # Porcentajes del período consultado
    # ==========================================
    #
    # Se evita dividir entre cero cuando el período
    # seleccionado todavía no tiene citas registradas.

    if total_appointments > 0:
        pending_percentage = round(
            pending_appointments
            / total_appointments
            * 100,
            1,
        )

        completed_percentage = round(
            completed_appointments
            / total_appointments
            * 100,
            1,
        )

        cancelled_percentage = round(
            cancelled_appointments
            / total_appointments
            * 100,
            1,
        )

    else:
        pending_percentage = 0
        completed_percentage = 0
        cancelled_percentage = 0

    # ==========================================
    # Datos para la gráfica de citas por fecha
    # ==========================================
    #
    # Las citas se agrupan según la fecha del cupo
    # asociado, respetando el período seleccionado.

    appointments_by_date = (
        appointments
        .annotate(
            appointment_date=TruncDate(
                "availability_slot__start_time",
                tzinfo=timezone.get_current_timezone(),
            ),
        )
        .values("appointment_date")
        .annotate(
            total=Count("id"),
        )
        .order_by("appointment_date")
    )

    chart_labels = []
    chart_values = []

    for item in appointments_by_date:
        appointment_date = item["appointment_date"]

        if appointment_date:
            chart_labels.append(
                appointment_date.strftime("%d/%m/%Y")
            )

            chart_values.append(
                item["total"]
            )

    # ==========================================
    # Reporte de actividad por psicólogo
    # ==========================================
    #
    # Se utilizan únicamente las citas que pertenecen
    # al período actualmente seleccionado.

    filtered_appointment_ids = appointments.values("id")

    psychologists_report = (
        Psychologist.objects
        .select_related("account")
        .annotate(
            total_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                ),
                distinct=True,
            ),
            pending_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.PENDING
                    ),
                ),
                distinct=True,
            ),
            confirmed_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.CONFIRMED
                    ),
                ),
                distinct=True,
            ),
            completed_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.COMPLETED
                    ),
                ),
                distinct=True,
            ),
            cancelled_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.CANCELLED
                    ),
                ),
                distinct=True,
            ),
            patients_attended_report=Count(
                "appointments__patient",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.COMPLETED
                    ),
                ),
                distinct=True,
            ),
        )
        .order_by(
            "account__first_name",
            "account__last_name",
        )
    )

    context = {
        "page_title": "Reportes",

        # Psicólogos.
        "total_psychologists": total_psychologists,
        "active_psychologist_accounts": (
            active_psychologist_accounts
        ),

        # Pacientes.
        "total_patients": total_patients,
        "active_patient_accounts": (
            active_patient_accounts
        ),

        # Citas.
        "total_appointments": total_appointments,
        "pending_appointments": pending_appointments,
        "confirmed_appointments": confirmed_appointments,
        "completed_appointments": completed_appointments,
        "cancelled_appointments": cancelled_appointments,

        # Porcentajes.
        "pending_percentage": pending_percentage,
        "completed_percentage": completed_percentage,
        "cancelled_percentage": cancelled_percentage,

        # Gráfica de citas por fecha.
        "chart_labels": chart_labels,
        "chart_values": chart_values,

        # Actividad por psicólogo.
        "psychologists_report": psychologists_report,

        # Filtros.
        "period_filter": period_filter,
        "start_date": start_date_raw,
        "end_date": end_date_raw,
        "date_filter_error": date_filter_error,
        "appointments_are_filtered": (
            appointments_are_filtered
        ),
        "period_summary": period_summary,
    }

    return render(
        request,
        "accounts/admin_report_dashboard.html",
        context,
    )


@login_required
def admin_report_appointments_csv(request):
    """
    Exporta las citas a un archivo CSV.

    La exportación respeta los mismos filtros disponibles
    en la pantalla de reportes:
    - Hoy.
    - Últimos 7 días.
    - Este mes.
    - Rango personalizado.
    - Historial completo.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    # ==========================================
    # Resolver el período de la exportación
    # ==========================================

    report_period = resolve_report_period(request)

    start_date = report_period["start_date"]
    end_date = report_period["end_date"]
    date_filter_error = report_period["date_filter_error"]

    # Si el rango recibido no es válido, se regresa
    # a la pantalla principal de reportes.
    if date_filter_error:
        return redirect("admin-report-dashboard")

    # ==========================================
    # Consultar citas
    # ==========================================

    appointments = (
        Appointment.objects
        .select_related(
            "patient__account",
            "psychologist__account",
            "availability_slot",
        )
        .order_by(
            "availability_slot__start_time",
        )
    )

    appointments = filter_appointments_by_period(
        appointments=appointments,
        start_date=start_date,
        end_date=end_date,
    )

    # ==========================================
    # Preparar la respuesta CSV
    # ==========================================

    response = HttpResponse(
        content_type="text/csv; charset=utf-8",
    )

    filename = "reporte_citas"

    if start_date and end_date:
        filename += (
            f"_{start_date.isoformat()}"
            f"_a_{end_date.isoformat()}"
        )

    elif start_date:
        filename += f"_desde_{start_date.isoformat()}"

    elif end_date:
        filename += f"_hasta_{end_date.isoformat()}"

    else:
        filename += "_historial_completo"

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}.csv"'
    )

    # Permite que Excel reconozca correctamente
    # caracteres como tildes y la letra ñ.
    response.write("\ufeff")

    writer = csv.writer(response)

    # ==========================================
    # Encabezados
    # ==========================================

    writer.writerow(
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
        ]
    )

    # ==========================================
    # Filas del reporte
    # ==========================================

    for appointment in appointments:
        local_start_time = timezone.localtime(
            appointment.availability_slot.start_time
        )

        local_end_time = timezone.localtime(
            appointment.availability_slot.end_time
        )

        psychologist_account = (
            appointment.psychologist.account
        )

        patient_account = appointment.patient.account

        psychologist_name = (
            f"{psychologist_account.first_name} "
            f"{psychologist_account.last_name}"
        ).strip()

        patient_name = (
            f"{patient_account.first_name} "
            f"{patient_account.last_name}"
        ).strip()

        if not psychologist_name:
            psychologist_name = psychologist_account.email

        if not patient_name:
            patient_name = patient_account.email

        cancelled_reason = appointment.cancelled_reason

        writer.writerow(
            [
                local_start_time.strftime("%d/%m/%Y"),
                local_start_time.strftime("%I:%M %p"),
                local_end_time.strftime("%I:%M %p"),
                psychologist_name,
                psychologist_account.email,
                patient_name,
                patient_account.email,
                appointment.get_status_display(),
                cancelled_reason or "",
            ]
        )

    return response


@login_required
def admin_report_psychologists_csv(request):
    """
    Exporta un resumen de actividad por psicólogo.

    La exportación respeta los mismos filtros disponibles
    en la pantalla de reportes:
    - Hoy.
    - Últimos 7 días.
    - Este mes.
    - Rango personalizado.
    - Historial completo.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    # ==========================================
    # Resolver el período de la exportación
    # ==========================================

    report_period = resolve_report_period(request)

    start_date = report_period["start_date"]
    end_date = report_period["end_date"]
    date_filter_error = report_period["date_filter_error"]

    # Si el rango recibido no es válido, se regresa
    # a la pantalla principal de reportes.
    if date_filter_error:
        return redirect("admin-report-dashboard")

    # ==========================================
    # Consultar las citas del período
    # ==========================================

    appointments = Appointment.objects.all()

    appointments = filter_appointments_by_period(
        appointments=appointments,
        start_date=start_date,
        end_date=end_date,
    )

    filtered_appointment_ids = appointments.values("id")

    # ==========================================
    # Resumen por psicólogo
    # ==========================================

    psychologists_report = (
        Psychologist.objects
        .select_related("account")
        .annotate(
            total_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                ),
                distinct=True,
            ),
            pending_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.PENDING
                    ),
                ),
                distinct=True,
            ),
            confirmed_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.CONFIRMED
                    ),
                ),
                distinct=True,
            ),
            completed_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.COMPLETED
                    ),
                ),
                distinct=True,
            ),
            cancelled_appointments_report=Count(
                "appointments",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.CANCELLED
                    ),
                ),
                distinct=True,
            ),
            patients_attended_report=Count(
                "appointments__patient",
                filter=Q(
                    appointments__id__in=(
                        filtered_appointment_ids
                    ),
                    appointments__status=(
                        Appointment.Status.COMPLETED
                    ),
                ),
                distinct=True,
            ),
        )
        .order_by(
            "account__first_name",
            "account__last_name",
        )
    )

    # ==========================================
    # Preparar la respuesta CSV
    # ==========================================

    response = HttpResponse(
        content_type="text/csv; charset=utf-8",
    )

    filename = "reporte_psicologos"

    if start_date and end_date:
        filename += (
            f"_{start_date.isoformat()}"
            f"_a_{end_date.isoformat()}"
        )

    elif start_date:
        filename += f"_desde_{start_date.isoformat()}"

    elif end_date:
        filename += f"_hasta_{end_date.isoformat()}"

    else:
        filename += "_historial_completo"

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}.csv"'
    )

    # Facilita que Excel reconozca correctamente
    # las tildes y la letra ñ.
    response.write("\ufeff")

    writer = csv.writer(response)

    writer.writerow(
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
        ]
    )

    for psychologist in psychologists_report:
        account = psychologist.account

        psychologist_name = (
            f"{account.first_name} "
            f"{account.last_name}"
        ).strip()

        if not psychologist_name:
            psychologist_name = account.email

        account_status = (
            "Activa"
            if account.is_active
            else "Inactiva"
        )

        writer.writerow(
            [
                psychologist_name,
                account.email,
                account_status,
                psychologist.total_appointments_report,
                psychologist.pending_appointments_report,
                psychologist.confirmed_appointments_report,
                psychologist.completed_appointments_report,
                psychologist.cancelled_appointments_report,
                psychologist.patients_attended_report,
            ]
        )

    return response