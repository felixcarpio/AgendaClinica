from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from apps.assignments.models import Assignment
from django.contrib import messages

from apps.assignments.forms import PatientAssignmentResponseForm

@login_required
def patient_assignment_list(request):
    """
    Muestra las asignaciones visibles del paciente autenticado.

    Se separan en:
    - asignaciones activas;
    - asignaciones completadas.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    assignments = (
        Assignment.objects
        .filter(
            session_note__clinical_record__patient__account=request.user,
            is_visible=True,
        )
        .select_related(
            "session_note",
            "session_note__appointment",
            "session_note__clinical_record",
            "session_note__clinical_record__patient",
        )
    )

    active_assignments = (
        assignments
        .filter(
            status__in=[
                Assignment.Status.PENDING,
                Assignment.Status.IN_PROGRESS,
            ]
        )
        .order_by("-created_at")
    )

    completed_assignments = (
        assignments
        .filter(
            status=Assignment.Status.COMPLETED,
        )
        .order_by("-completed_at", "-created_at")
    )

    context = {
        "page_title": "Mis asignaciones",
        "active_assignments": active_assignments,
        "completed_assignments": completed_assignments,
    }

    return render(
        request,
        "assignments/patient_assignment_list.html",
        context,
    )
    
@login_required
def patient_assignment_detail(request, public_id):
    """
    Muestra y procesa la respuesta de una asignación visible
    perteneciente al paciente autenticado.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "session_note",
            "session_note__appointment",
            "session_note__appointment__psychologist",
            "session_note__appointment__psychologist__account",
            "session_note__appointment__availability_slot",
            "session_note__clinical_record",
            "session_note__clinical_record__patient",
        ).prefetch_related(
            "attachments",
        ),
        public_id=public_id,
        session_note__clinical_record__patient__account=request.user,
        is_visible=True,
    )

    if request.method == "POST":
        form = PatientAssignmentResponseForm(
            request.POST,
            instance=assignment,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Tu respuesta se guardó correctamente.",
            )

            return redirect(
                "patient-assignment-detail",
                public_id=assignment.public_id,
            )
    else:
        form = PatientAssignmentResponseForm(
            instance=assignment,
        )

    context = {
        "page_title": "Detalle de la asignación",
        "assignment": assignment,
        "form": form,
    }

    return render(
        request,
        "assignments/patient_assignment_detail.html",
        context,
    )