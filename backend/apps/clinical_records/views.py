from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

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
    Muestra todas las notas de sesión pertenecientes
    al psicólogo autenticado.

    Las notas se ordenan desde la sesión más reciente
    hasta la más antigua.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

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
        .prefetch_related(
            "assignments",
        )
        .order_by(
            "-appointment__availability_slot__start_time",
        )
    )

    context = {
        "page_title": "Notas de sesión",
        "session_notes": session_notes,
        "session_notes_count": session_notes.count(),
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

    El psicólogo solo puede consultar pacientes con los que
    tenga o haya tenido citas registradas.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    patient = get_object_or_404(
        Patient.objects.select_related(
            "account",
        ).filter(
            appointments__psychologist__account=request.user,
        ).distinct(),
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

    El psicólogo solo puede editar expedientes de pacientes
    con los que tenga o haya tenido citas registradas.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    patient = get_object_or_404(
        Patient.objects.select_related(
            "account",
        ).filter(
            appointments__psychologist__account=request.user,
        ).distinct(),
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