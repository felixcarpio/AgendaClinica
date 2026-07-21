from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from apps.patients.models import Patient
from apps.appointments.models import Appointment
from apps.clinical_records.forms import (
    ClinicalRecordForm,
    SessionNoteForm,
)
from apps.clinical_records.models import ClinicalRecord, SessionNote


@login_required
def psychologist_session_note_list(request):
    """
    Muestra las notas de sesión pertenecientes al psicólogo autenticado.

    Permite:

    - Buscar por nombre o apellido del paciente.
    - Filtrar por rango de fechas.
    - Filtrar notas con o sin asignaciones.
    - Ordenar por fecha de sesión.
    - Paginar los resultados.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    query = request.GET.get("q", "").strip()
    date_from_value = request.GET.get("date_from", "").strip()
    date_to_value = request.GET.get("date_to", "").strip()
    assignment_filter = (
        request.GET.get("assignments", "")
        .strip()
        .lower()
    )
    ordering = (
        request.GET.get("ordering", "newest")
        .strip()
        .lower()
    )

    allowed_assignment_filters = {
        "with",
        "without",
    }

    if assignment_filter not in allowed_assignment_filters:
        assignment_filter = ""

    allowed_ordering = {
        "newest",
        "oldest",
    }

    if ordering not in allowed_ordering:
        ordering = "newest"

    date_from = (
        parse_date(date_from_value)
        if date_from_value
        else None
    )

    date_to = (
        parse_date(date_to_value)
        if date_to_value
        else None
    )

    session_notes = (
        SessionNote.objects
        .filter(
            appointment__psychologist__account=request.user,
        )
        .select_related(
            "appointment",
            "appointment__availability_slot",
            "appointment__patient",
            "appointment__patient__account",
            "clinical_record",
            "clinical_record__patient",
            "clinical_record__patient__account",
        )
        .annotate(
            assignments_count=Count(
                "assignments",
                distinct=True,
            ),
        )
    )

    # Búsqueda parcial por nombre o apellido.
    if query:
        session_notes = session_notes.filter(
            Q(
                appointment__patient__account__first_name__icontains=(
                    query
                )
            )
            | Q(
                appointment__patient__account__last_name__icontains=(
                    query
                )
            )
        )

    # Filtro desde una fecha determinada.
    if date_from:
        session_notes = session_notes.filter(
            appointment__availability_slot__start_time__date__gte=(
                date_from
            ),
        )

    # Filtro hasta una fecha determinada.
    if date_to:
        session_notes = session_notes.filter(
            appointment__availability_slot__start_time__date__lte=(
                date_to
            ),
        )

    # Filtro según existencia de asignaciones.
    if assignment_filter == "with":
        session_notes = session_notes.filter(
            assignments_count__gt=0,
        )

    elif assignment_filter == "without":
        session_notes = session_notes.filter(
            assignments_count=0,
        )

    # Orden cronológico.
    if ordering == "oldest":
        session_notes = session_notes.order_by(
            "appointment__availability_slot__start_time",
        )

    else:
        session_notes = session_notes.order_by(
            "-appointment__availability_slot__start_time",
        )

    filtered_notes_count = session_notes.count()

    paginator = Paginator(
        session_notes,
        10,
    )

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_title": "Notas de sesión",
        "page_obj": page_obj,
        "query": query,
        "date_from": date_from_value,
        "date_to": date_to_value,
        "assignment_filter": assignment_filter,
        "ordering": ordering,
        "filtered_notes_count": filtered_notes_count,
    }

    return render(
        request,
        "clinical_records/psychologist_session_note_list.html",
        context,
    )


@login_required
def psychologist_session_note_manage(request, appointment_public_id):
    """
    Permite al psicólogo crear o actualizar la nota clínica
    correspondiente a una cita completada.

    La cita debe:
    - pertenecer al psicólogo autenticado;
    - haber finalizado;
    - encontrarse en estado completado.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "patient",
            "patient__account",
            "psychologist",
            "psychologist__account",
            "availability_slot",
        ),
        public_id=appointment_public_id,
        psychologist__account=request.user,
    )

    if appointment.status != Appointment.Status.COMPLETED:
        messages.error(
            request,
            "Solo puedes registrar notas para citas completadas.",
        )

        return redirect(
            "psychologist-appointment-detail",
            public_id=appointment.public_id,
        )

    if appointment.availability_slot.end_time > timezone.now():
        messages.error(
            request,
            "No puedes registrar la nota antes de que finalice la cita.",
        )

        return redirect(
            "psychologist-appointment-detail",
            public_id=appointment.public_id,
        )

    clinical_record, _ = ClinicalRecord.objects.get_or_create(
        patient=appointment.patient,
    )

    session_note = SessionNote.objects.filter(
        appointment=appointment,
    ).first()

    if request.method == "POST":
        form = SessionNoteForm(
            request.POST,
            instance=session_note,
        )

        if form.is_valid():
            note = form.save(commit=False)
            note.clinical_record = clinical_record
            note.appointment = appointment
            note.save()

            messages.success(
                request,
                "La nota de sesión fue guardada correctamente.",
            )

            return redirect(
                "psychologist-appointment-detail",
                public_id=appointment.public_id,
            )
    else:
        form = SessionNoteForm(
            instance=session_note,
        )

    context = {
        "page_title": "Nota de sesión",
        "appointment": appointment,
        "patient": appointment.patient,
        "clinical_record": clinical_record,
        "session_note": session_note,
        "form": form,
    }

    return render(
        request,
        "clinical_records/psychologist_session_note_form.html",
        context,
    )


@login_required
def psychologist_clinical_record_detail(request, patient_public_id):
    """
    Muestra el expediente clínico de un paciente vinculado
    con el psicólogo autenticado.

    El acceso depende de la relación explícita entre
    paciente y psicólogo, no de la existencia de citas.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    patient = get_object_or_404(
        Patient.objects
        .select_related(
            "account",
        )
        .filter(
            psychologist_relationships__psychologist__account=(
                request.user
            ),
        )
        .distinct(),
        public_id=patient_public_id,
    )

    clinical_record, _ = ClinicalRecord.objects.get_or_create(
        patient=patient,
    )

    session_notes = (
        clinical_record.session_notes
        .filter(
            appointment__psychologist__account=request.user,
        )
        .select_related(
            "appointment",
            "appointment__availability_slot",
            "appointment__psychologist",
        )
        .order_by(
            "-appointment__availability_slot__start_time",
        )
    )

    context = {
        "page_title": "Expediente clínico",
        "patient": patient,
        "clinical_record": clinical_record,
        "session_notes": session_notes,
    }

    return render(
        request,
        "clinical_records/psychologist_clinical_record_detail.html",
        context,
    )


@login_required
def psychologist_clinical_record_edit(request, patient_public_id):
    """
    Permite al psicólogo actualizar la información general
    del expediente clínico de un paciente vinculado.

    El acceso depende de la relación explícita entre
    paciente y psicólogo, no de la existencia de citas.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    patient = get_object_or_404(
        Patient.objects
        .select_related(
            "account",
        )
        .filter(
            psychologist_relationships__psychologist__account=(
                request.user
            ),
        )
        .distinct(),
        public_id=patient_public_id,
    )

    clinical_record, _ = ClinicalRecord.objects.get_or_create(
        patient=patient,
    )

    if request.method == "POST":
        form = ClinicalRecordForm(
            request.POST,
            instance=clinical_record,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "El expediente clínico fue actualizado correctamente.",
            )

            return redirect(
                "psychologist-clinical-record-detail",
                patient_public_id=patient.public_id,
            )
    else:
        form = ClinicalRecordForm(
            instance=clinical_record,
        )

    context = {
        "page_title": "Editar expediente clínico",
        "patient": patient,
        "clinical_record": clinical_record,
        "form": form,
    }

    return render(
        request,
        "clinical_records/psychologist_clinical_record_form.html",
        context,
    )