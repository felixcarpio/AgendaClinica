from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from apps.patients.models import Patient


@login_required
def psychologist_patient_list(request):
    """
    Muestra los pacientes que tienen o han tenido citas
    con el psicólogo autenticado.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    patients = (
        Patient.objects
        .filter(
            appointments__psychologist__account=request.user,
        )
        .select_related(
            "account",
        )
        .distinct()
        .order_by(
            "account__first_name",
            "account__last_name",
        )
    )

    context = {
        "page_title": "Mis pacientes",
        "patients": patients,
    }

    return render(
        request,
        "patients/psychologist_patient_list.html",
        context,
    )
    
@login_required
def psychologist_patient_detail(request, public_id):
    """
    Muestra el detalle de un paciente que tiene o ha tenido
    citas con el psicólogo autenticado.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    patient = get_object_or_404(
        Patient.objects.select_related(
            "account",
        ).filter(
            appointments__psychologist__account=request.user,
        ).distinct(),
        public_id=public_id,
    )

    appointments = (
        patient.appointments
        .filter(
            psychologist__account=request.user,
        )
        .select_related(
            "availability_slot",
            "psychologist",
        )
        .order_by(
            "-availability_slot__start_time",
        )
    )

    completed_appointments = appointments.filter(
        status="COMPLETED",
    )

    upcoming_appointments = appointments.filter(
        status__in=[
            "PENDING",
            "CONFIRMED",
        ],
    ).order_by(
        "availability_slot__start_time",
    )

    context = {
        "page_title": "Detalle del paciente",
        "patient": patient,
        "upcoming_appointments": upcoming_appointments,
        "completed_appointments": completed_appointments,
    }

    return render(
        request,
        "patients/psychologist_patient_detail.html",
        context,
    )