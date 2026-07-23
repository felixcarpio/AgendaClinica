from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from apps.appointments.models import Appointment
from apps.accounts.models import Account
from apps.assignments.models import Assignment
from apps.patients.models import Patient
from apps.psychologists.models import Psychologist
from django.core.paginator import Paginator
from datetime import timedelta
from django.db.models import Q

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
            session_note__appointment__psychologist__account=request.user,
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

    patient = Patient.objects.select_related(
        "account"
    ).get(
        account=request.user
    )
    
    if patient.gender == Patient.Gender.FEMALE:
        welcome_text = "Bienvenida"
    else:
        welcome_text = "Bienvenido"
        
    now = timezone.now()

    appointments = (
        Appointment.objects
        .filter(patient__account=request.user)
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
        .order_by("availability_slot__start_time")
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
            session_note__clinical_record__patient__account=request.user,
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
    # Filtros de fecha para citas
    # ==========================================

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

    if period_filter == "today":
        start_date = today
        end_date = today

        start_date_raw = today.isoformat()
        end_date_raw = today.isoformat()

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
        period_filter = ""

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

    appointments = Appointment.objects.all()

    # Solo se aplican los filtros cuando las fechas son válidas.
    if not date_filter_error:
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

    # ==========================================
    # Citas agrupadas por estado
    # ==========================================

    total_appointments = appointments.count()

    confirmed_appointments = appointments.filter(
        status=Appointment.Status.CONFIRMED,
    ).count()

    completed_appointments = appointments.filter(
        status=Appointment.Status.COMPLETED,
    ).count()

    cancelled_appointments = appointments.filter(
        status=Appointment.Status.CANCELLED,
    ).count()
    
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
        "confirmed_appointments": confirmed_appointments,
        "completed_appointments": completed_appointments,
        "cancelled_appointments": cancelled_appointments,

        # Filtros.
        "start_date": start_date_raw,
        "end_date": end_date_raw,
        "date_filter_error": date_filter_error,
        "appointments_are_filtered": bool(
            start_date or end_date
        ),
        "period_filter": period_filter,
        "period_summary": period_summary,
    }

    return render(
        request,
        "accounts/admin_report_dashboard.html",
        context,
    )