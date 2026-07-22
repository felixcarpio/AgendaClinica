from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.assignments.forms import (
    PatientAssignmentResponseForm,
    PatientAssignmentAttachmentForm,
    PsychologistAssignmentAttachmentForm,
    PsychologistAssignmentForm,
)
from apps.assignments.models import Assignment, AssignmentAttachment
from apps.clinical_records.models import SessionNote


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
    
@login_required
def psychologist_assignment_general_list(request):
    """
    Muestra todas las asignaciones pertenecientes
    al psicólogo autenticado.

    Permite:
    - buscar por paciente, título o descripción;
    - filtrar por estado;
    - ordenar los resultados;
    - paginar el listado.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    query = request.GET.get(
        "q",
        "",
    ).strip()

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    ordering = request.GET.get(
        "ordering",
        "updated",
    ).strip()

    base_assignments = (
        Assignment.objects
        .filter(
            session_note__appointment__psychologist__account=request.user,
        )
        .select_related(
            "session_note",
            "session_note__appointment",
            "session_note__appointment__availability_slot",
            "session_note__clinical_record",
            "session_note__clinical_record__patient",
            "session_note__clinical_record__patient__account",
        )
        .annotate(
            attachments_count=Count(
                "attachments",
                distinct=True,
            ),
        )
    )

    active_assignments_count = base_assignments.filter(
        status__in=[
            Assignment.Status.PENDING,
            Assignment.Status.IN_PROGRESS,
        ],
    ).count()

    completed_assignments_count = base_assignments.filter(
        status=Assignment.Status.COMPLETED,
    ).count()

    cancelled_assignments_count = base_assignments.filter(
        status=Assignment.Status.CANCELLED,
    ).count()

    assignments = base_assignments

    if query:
        assignments = assignments.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(
                session_note__clinical_record__patient__account__first_name__icontains=query
            )
            | Q(
                session_note__clinical_record__patient__account__last_name__icontains=query
            )
        )

    valid_statuses = {
        Assignment.Status.PENDING,
        Assignment.Status.IN_PROGRESS,
        Assignment.Status.COMPLETED,
        Assignment.Status.CANCELLED,
    }

    if status_filter in valid_statuses:
        assignments = assignments.filter(
            status=status_filter,
        )
    else:
        status_filter = ""

    if ordering == "newest":
        assignments = assignments.order_by(
            "-created_at",
        )

    elif ordering == "oldest":
        assignments = assignments.order_by(
            "created_at",
        )

    elif ordering == "patient":
        assignments = assignments.order_by(
            "session_note__clinical_record__patient__account__first_name",
            "session_note__clinical_record__patient__account__last_name",
        )

    else:
        ordering = "updated"

        assignments = assignments.order_by(
            "-updated_at",
        )

    filtered_assignments_count = assignments.count()

    paginator = Paginator(
        assignments,
        10,
    )

    page_obj = paginator.get_page(
        request.GET.get("page"),
    )

    context = {
        "page_title": "Asignaciones",
        "page_obj": page_obj,
        "query": query,
        "status_filter": status_filter,
        "ordering": ordering,
        "filtered_assignments_count": filtered_assignments_count,
        "active_assignments_count": active_assignments_count,
        "completed_assignments_count": completed_assignments_count,
        "cancelled_assignments_count": cancelled_assignments_count,
    }

    return render(
        request,
        "assignments/psychologist_assignment_general_list.html",
        context,
    )

@login_required
def psychologist_assignment_list(request, note_public_id):
    """
    Muestra las asignaciones asociadas a una nota de sesión.

    Permite:
    - buscar por título o descripción;
    - filtrar por estado;
    - ordenar por fecha de creación o actualización;
    - paginar los resultados.

    La nota debe pertenecer a una cita atendida por
    el psicólogo autenticado.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    session_note = get_object_or_404(
        SessionNote.objects.select_related(
            "clinical_record",
            "clinical_record__patient",
            "clinical_record__patient__account",
            "appointment",
            "appointment__psychologist",
            "appointment__psychologist__account",
            "appointment__availability_slot",
        ),
        public_id=note_public_id,
        appointment__psychologist__account=request.user,
    )

    # Parámetros recibidos desde el formulario de filtros.
    query = request.GET.get(
        "q",
        "",
    ).strip()

    status_filter = request.GET.get(
        "status",
        "",
    ).strip()

    ordering = request.GET.get(
        "ordering",
        "newest",
    ).strip()

    assignments = (
        session_note.assignments
        .annotate(
            attachments_count=Count(
                "attachments",
                distinct=True,
            ),
        )
    )

    # Busca coincidencias en el título y la descripción.
    if query:
        assignments = assignments.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
        )

    # Aplica el filtro de estado solo cuando el valor es válido.
    valid_statuses = {
        Assignment.Status.PENDING,
        Assignment.Status.IN_PROGRESS,
        Assignment.Status.COMPLETED,
        Assignment.Status.CANCELLED,
    }

    if status_filter in valid_statuses:
        assignments = assignments.filter(
            status=status_filter,
        )
    else:
        status_filter = ""

    # Define el orden de los resultados.
    if ordering == "oldest":
        assignments = assignments.order_by(
            "created_at",
        )
    elif ordering == "updated":
        assignments = assignments.order_by(
            "-updated_at",
        )
    else:
        ordering = "newest"

        assignments = assignments.order_by(
            "-created_at",
        )

    filtered_assignments_count = assignments.count()

    # Muestra hasta diez asignaciones por página.
    paginator = Paginator(
        assignments,
        10,
    )

    page_obj = paginator.get_page(
        request.GET.get("page"),
    )

    context = {
        "page_title": "Asignaciones de la sesión",
        "session_note": session_note,
        "appointment": session_note.appointment,
        "patient": session_note.clinical_record.patient,
        "page_obj": page_obj,
        "query": query,
        "status_filter": status_filter,
        "ordering": ordering,
        "filtered_assignments_count": filtered_assignments_count,
    }

    return render(
        request,
        "assignments/psychologist_assignment_list.html",
        context,
    )
    
@login_required
def psychologist_assignment_create(request, note_public_id):
    """
    Permite crear una asignación asociada a una nota de sesión.

    La nota se obtiene desde la URL y no puede seleccionarse
    manualmente desde el formulario.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    session_note = get_object_or_404(
        SessionNote.objects.select_related(
            "clinical_record",
            "clinical_record__patient",
            "clinical_record__patient__account",
            "appointment",
            "appointment__psychologist",
            "appointment__psychologist__account",
            "appointment__availability_slot",
        ),
        public_id=note_public_id,
        appointment__psychologist__account=request.user,
    )

    if request.method == "POST":
        form = PsychologistAssignmentForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            with transaction.atomic():
                assignment = form.save(
                    commit=False,
                )

                assignment.session_note = session_note
                assignment.save()

                uploaded_files = form.cleaned_data.get(
                    "attachments",
                    [],
                )

                for uploaded_file in uploaded_files:
                    AssignmentAttachment.objects.create(
                        assignment=assignment,
                        file=uploaded_file,
                        uploaded_by=(
                            AssignmentAttachment
                            .UploadedBy
                            .PSYCHOLOGIST
                        ),
                    )

            messages.success(
                request,
                "La asignación fue creada correctamente.",
            )

            return redirect(
                "psychologist-assignment-list",
                note_public_id=session_note.public_id,
            )
    else:
        form = PsychologistAssignmentForm(
            initial={
                "status": Assignment.Status.PENDING,
            },
        )

    context = {
        "page_title": "Nueva asignación",
        "session_note": session_note,
        "appointment": session_note.appointment,
        "patient": session_note.clinical_record.patient,
        "form": form,
    }

    return render(
        request,
        "assignments/psychologist_assignment_form.html",
        context,
    )
    
@login_required
def psychologist_assignment_edit(request, public_id):
    """
    Permite al psicólogo actualizar una asignación
    perteneciente a una de sus sesiones.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "session_note",
            "session_note__clinical_record",
            "session_note__clinical_record__patient",
            "session_note__clinical_record__patient__account",
            "session_note__appointment",
            "session_note__appointment__psychologist",
            "session_note__appointment__psychologist__account",
            "session_note__appointment__availability_slot",
        ).prefetch_related(
            "attachments",
        ),
        public_id=public_id,
        session_note__appointment__psychologist__account=request.user,
    )

    if request.method == "POST":
        form = PsychologistAssignmentForm(
            request.POST,
            instance=assignment,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "La asignación fue actualizada correctamente.",
            )

            return redirect(
                "psychologist-assignment-list",
                note_public_id=assignment.session_note.public_id,
            )
    else:
        form = PsychologistAssignmentForm(
            instance=assignment,
        )

    context = {
        "page_title": "Editar asignación",
        "assignment": assignment,
        "session_note": assignment.session_note,
        "appointment": assignment.session_note.appointment,
        "patient": assignment.session_note.clinical_record.patient,
        "form": form,
        "attachments": assignment.attachments.all(),
    }

    return render(
        request,
        "assignments/psychologist_assignment_form.html",
        context,
    )
    
@login_required
def psychologist_assignment_attachment_upload(request, public_id):
    """
    Permite al psicólogo adjuntar un archivo a una asignación
    perteneciente a una de sus sesiones.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "session_note",
            "session_note__appointment",
            "session_note__appointment__psychologist",
            "session_note__appointment__psychologist__account",
            "session_note__clinical_record",
            "session_note__clinical_record__patient",
            "session_note__clinical_record__patient__account",
        ),
        public_id=public_id,
        session_note__appointment__psychologist__account=request.user,
    )

    if request.method == "POST":
        form = PsychologistAssignmentAttachmentForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.assignment = assignment
            attachment.uploaded_by = (
                AssignmentAttachment.UploadedBy.PSYCHOLOGIST
            )
            attachment.save()

            messages.success(
                request,
                "El archivo fue adjuntado correctamente.",
            )

            return redirect(
                "psychologist-assignment-edit",
                public_id=assignment.public_id,
            )
    else:
        form = PsychologistAssignmentAttachmentForm()

    context = {
        "page_title": "Adjuntar archivo",
        "assignment": assignment,
        "session_note": assignment.session_note,
        "appointment": assignment.session_note.appointment,
        "patient": assignment.session_note.clinical_record.patient,
        "form": form,
    }

    return render(
        request,
        "assignments/psychologist_assignment_attachment_form.html",
        context,
    )
    
@login_required
def psychologist_assignment_attachment_delete(request, attachment_id):
    """
    Permite al psicólogo eliminar un archivo adjunto
    perteneciente a una de sus asignaciones.

    La eliminación solo se permite mediante una solicitud POST.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    attachment = get_object_or_404(
        AssignmentAttachment.objects.select_related(
            "assignment",
            "assignment__session_note",
            "assignment__session_note__appointment",
            "assignment__session_note__appointment__psychologist",
            "assignment__session_note__appointment__psychologist__account",
        ),
        id=attachment_id,
        assignment__session_note__appointment__psychologist__account=request.user,
    )

    assignment = attachment.assignment

    if request.method != "POST":
        return redirect(
            "psychologist-assignment-edit",
            public_id=assignment.public_id,
        )

    # Elimina primero el archivo físico almacenado en MEDIA_ROOT.
    if attachment.file:
        attachment.file.delete(save=False)

    # Elimina posteriormente el registro de la base de datos.
    attachment.delete()

    messages.success(
        request,
        "El archivo adjunto fue eliminado correctamente.",
    )

    return redirect(
        "psychologist-assignment-edit",
        public_id=assignment.public_id,
    )
    
@login_required
def patient_assignment_attachment_upload(request, public_id):
    """
    Permite al paciente adjuntar un archivo como parte
    de su respuesta a una asignación visible.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    assignment = get_object_or_404(
        Assignment.objects.select_related(
            "session_note",
            "session_note__clinical_record",
            "session_note__clinical_record__patient",
            "session_note__clinical_record__patient__account",
        ),
        public_id=public_id,
        session_note__clinical_record__patient__account=request.user,
        is_visible=True,
    )

    if assignment.status == Assignment.Status.CANCELLED:
        messages.error(
            request,
            "No puedes adjuntar archivos a una asignación cancelada.",
        )

        return redirect(
            "patient-assignment-detail",
            public_id=assignment.public_id,
        )

    if request.method == "POST":
        form = PatientAssignmentAttachmentForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.assignment = assignment
            attachment.uploaded_by = (
                AssignmentAttachment.UploadedBy.PATIENT
            )
            attachment.save()

            messages.success(
                request,
                "El archivo fue adjuntado correctamente.",
            )

            return redirect(
                "patient-assignment-detail",
                public_id=assignment.public_id,
            )
    else:
        form = PatientAssignmentAttachmentForm()

    context = {
        "page_title": "Adjuntar archivo",
        "assignment": assignment,
        "form": form,
    }

    return render(
        request,
        "assignments/patient_assignment_attachment_form.html",
        context,
    )
    
@login_required
def patient_assignment_attachment_delete(request, attachment_id):
    """
    Permite al paciente eliminar únicamente los archivos
    que él mismo haya subido a una asignación propia.

    La eliminación solo se permite mediante POST.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    attachment = get_object_or_404(
        AssignmentAttachment.objects.select_related(
            "assignment",
            "assignment__session_note",
            "assignment__session_note__clinical_record",
            "assignment__session_note__clinical_record__patient",
            "assignment__session_note__clinical_record__patient__account",
        ),
        id=attachment_id,
        uploaded_by=AssignmentAttachment.UploadedBy.PATIENT,
        assignment__session_note__clinical_record__patient__account=request.user,
        assignment__is_visible=True,
    )

    assignment = attachment.assignment

    if request.method != "POST":
        return redirect(
            "patient-assignment-detail",
            public_id=assignment.public_id,
        )

    if attachment.file:
        attachment.file.delete(save=False)

    attachment.delete()

    messages.success(
        request,
        "El archivo adjunto fue eliminado correctamente.",
    )

    return redirect(
        "patient-assignment-detail",
        public_id=assignment.public_id,
    )