from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from apps.appointments.models import Appointment
from apps.assignments.models import Assignment
from apps.patients.models import Patient

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
    Muestra el dashboard exclusivo para usuarios administradores.
    """

    if request.user.role != "ADMIN":
        return redirect("dashboard-redirect")

    context = {
        "page_title": "Panel de administración",
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

    context = {
        "page_title": "Panel del psicólogo",
        "next_appointment": next_appointment,
        "today_appointments": today_appointments,
        "today_appointments_count": today_appointments.count(),
        "attended_patients_count": attended_patients_count,
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