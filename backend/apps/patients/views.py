from django.contrib.auth.decorators import login_required
import logging
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.utils.crypto import get_random_string
from django.core.paginator import Paginator
from django.db.models import OuterRef, Prefetch, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.accounts.models import Account
from apps.clinical_records.models import ClinicalRecord
from apps.patients.forms import (
    PsychologistPatientCreateForm,
    PsychologistPatientStatusForm,
)
from apps.patients.models import (
    Patient,
    PatientPsychologistRelationship,
)

logger = logging.getLogger(__name__)

@login_required
def psychologist_patient_create(request):
    """
    Permite que el psicólogo autenticado registre un paciente nuevo.

    La operación crea en una sola transacción:

    - La cuenta con rol de paciente.
    - El perfil administrativo del paciente.
    - La relación activa con el psicólogo.
    - El expediente clínico inicial.

    Si alguna creación falla, la transacción completa se revierte.
    """

    if request.user.role != Account.Role.PSYCHOLOGIST:
        return redirect("dashboard-redirect")

    psychologist = getattr(
        request.user,
        "psychologist_profile",
        None,
    )

    if psychologist is None:
        messages.error(
            request,
            (
                "Tu cuenta no tiene un perfil de psicólogo "
                "asociado."
            ),
        )

        return redirect("dashboard-redirect")

    if request.method == "POST":
        form = PsychologistPatientCreateForm(
            request.POST,
        )

        if form.is_valid():
            temporary_password = get_random_string(
                length=12,
                allowed_chars=(
                    "abcdefghjkmnpqrstuvwxyz"
                    "ABCDEFGHJKMNPQRSTUVWXYZ"
                    "23456789"
                    "@#$%"
                ),
            )

            try:
                with transaction.atomic():
                    account = Account(
                        email=form.cleaned_data["email"],
                        first_name=form.cleaned_data["first_name"],
                        last_name=form.cleaned_data["last_name"],
                        role=Account.Role.PATIENT,
                        is_active=True,
                        is_staff=False,
                    )

                    account.set_password(
                        temporary_password,
                    )

                    account.full_clean()
                    account.save()

                    patient = Patient(
                        account=account,
                        phone=form.cleaned_data["phone"],
                        birth_date=form.cleaned_data["birth_date"],
                        gender=form.cleaned_data["gender"],
                        status=Patient.Status.ACTIVE,
                        address=form.cleaned_data["address"],
                        emergency_contact_name=(
                            form.cleaned_data[
                                "emergency_contact_name"
                            ]
                        ),
                        emergency_contact_phone=(
                            form.cleaned_data[
                                "emergency_contact_phone"
                            ]
                        ),
                    )

                    patient.full_clean()
                    patient.save()

                    relationship = (
                        PatientPsychologistRelationship(
                            patient=patient,
                            psychologist=psychologist,
                            status=(
                                PatientPsychologistRelationship
                                .Status
                                .ACTIVE
                            ),
                        )
                    )

                    relationship.save()

                    clinical_record = ClinicalRecord(
                        patient=patient,
                        chief_complaint=(
                            form.cleaned_data[
                                "chief_complaint"
                            ]
                        ),
                    )

                    clinical_record.full_clean()
                    clinical_record.save()

            except IntegrityError:
                form.add_error(
                    "email",
                    (
                        "No fue posible registrar la cuenta. "
                        "El correo podría estar siendo utilizado."
                    ),
                )

            except Exception:
                logger.exception(
                    "Error al registrar un paciente desde el portal del psicólogo."
                )
                form.add_error(
                    None,
                    (
                        "No fue posible registrar al paciente. "
                        "Verifica los datos e inténtalo nuevamente."
                    ),
                )

            else:
                # Las credenciales se guardan temporalmente
                # para mostrarlas una sola vez después del registro.
                request.session[
                    "new_patient_credentials"
                ] = {
                    "patient_public_id": str(
                        patient.public_id
                    ),
                    "patient_name": (
                        f"{account.first_name} "
                        f"{account.last_name}"
                    ),
                    "email": account.email,
                    "temporary_password": (
                        temporary_password
                    ),
                }

                messages.success(
                    request,
                    "El paciente fue registrado correctamente.",
                )

                return redirect(
                    "psychologist-patient-created",
                )

    else:
        form = PsychologistPatientCreateForm()

    context = {
        "page_title": "Nuevo paciente",
        "form": form,
    }

    return render(
        request,
        "patients/psychologist_patient_create.html",
        context,
    )
    
@login_required
def psychologist_patient_created(request):
    """
    Muestra las credenciales temporales del paciente recién creado.

    La información se elimina de la sesión después de leerla,
    por lo que solo puede mostrarse una vez.
    """

    if request.user.role != Account.Role.PSYCHOLOGIST:
        return redirect("dashboard-redirect")

    credentials = request.session.pop(
        "new_patient_credentials",
        None,
    )

    if credentials is None:
        return redirect(
            "psychologist-patient-list",
        )

    context = {
        "page_title": "Paciente registrado",
        "credentials": credentials,
    }

    return render(
        request,
        "patients/psychologist_patient_created.html",
        context,
    )

@login_required
def psychologist_patient_list(request):
    """
    Muestra los pacientes vinculados al psicólogo autenticado.

    La vinculación se obtiene mediante la relación explícita
    entre paciente y psicólogo, por lo que un paciente puede
    aparecer aunque todavía no tenga citas registradas.

    Permite buscar por nombre o apellido y filtrar según
    el estado actual de la relación terapéutica.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    now = timezone.now()
    today = timezone.localdate()

    # Texto ingresado en la barra de búsqueda.
    query = request.GET.get("q", "").strip()

    # Estado seleccionado en los filtros.
    status_filter = (
        request.GET.get("status", "")
        .strip()
        .upper()
    )

    allowed_status_filters = {
        PatientPsychologistRelationship.Status.ACTIVE,
        PatientPsychologistRelationship.Status.INACTIVE,
        PatientPsychologistRelationship.Status.DISCHARGED,
    }

    if status_filter not in allowed_status_filters:
        status_filter = ""

    # Obtiene el estado de la relación más reciente entre
    # cada paciente y el psicólogo autenticado.
    latest_relationship_status = (
        PatientPsychologistRelationship.objects
        .filter(
            patient_id=OuterRef("pk"),
            psychologist__account=request.user,
        )
        .order_by(
            "-started_at",
            "-id",
        )
        .values("status")[:1]
    )

    # Citas del psicólogo que se cargarán junto con cada paciente.
    #
    # Prefetch evita ejecutar una consulta individual por
    # cada paciente mostrado en la tabla.
    psychologist_appointments = (
        Appointment.objects
        .filter(
            psychologist__account=request.user,
        )
        .select_related(
            "availability_slot",
            "psychologist",
        )
        .order_by(
            "availability_slot__start_time",
        )
    )

    # Pacientes vinculados directamente al psicólogo.
    #
    # Ya no dependemos de que exista una cita para que
    # el paciente aparezca en el listado.
    base_patients = (
        Patient.objects
        .filter(
            psychologist_relationships__psychologist__account=request.user,
        )
        .annotate(
            current_relationship_status=Subquery(
                latest_relationship_status,
            ),
        )
        .select_related(
            "account",
        )
        .prefetch_related(
            Prefetch(
                "appointments",
                queryset=psychologist_appointments,
                to_attr="psychologist_appointments",
            ),
        )
        .distinct()
        .order_by(
            "account__first_name",
            "account__last_name",
        )
    )

    # Las métricas generales no cambian al buscar o filtrar.
    total_patients_count = base_patients.count()

    active_patients_count = (
        base_patients
        .filter(
            current_relationship_status=(
                PatientPsychologistRelationship.Status.ACTIVE
            ),
        )
        .count()
    )

    inactive_patients_count = (
        base_patients
        .filter(
            current_relationship_status=(
                PatientPsychologistRelationship.Status.INACTIVE
            ),
        )
        .count()
    )

    discharged_patients_count = (
        base_patients
        .filter(
            current_relationship_status=(
                PatientPsychologistRelationship.Status.DISCHARGED
            ),
        )
        .count()
    )

    today_sessions_count = (
        Appointment.objects
        .filter(
            psychologist__account=request.user,
            availability_slot__start_time__date=today,
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.CONFIRMED,
            ],
        )
        .count()
    )

    completed_sessions_count = (
        Appointment.objects
        .filter(
            psychologist__account=request.user,
            status=Appointment.Status.COMPLETED,
        )
        .count()
    )

    patients = base_patients

    # Búsqueda parcial por nombre o apellido.
    if query:
        patients = patients.filter(
            Q(account__first_name__icontains=query)
            | Q(account__last_name__icontains=query)
        )

    # Filtro por estado de la relación terapéutica.
    if status_filter:
        patients = patients.filter(
            current_relationship_status=status_filter,
        )

    filtered_patients_count = patients.count()

    # Se muestran diez pacientes por página.
    paginator = Paginator(
        patients,
        10,
    )

    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calcula la última sesión completada y la próxima cita
    # usando las citas precargadas.
    for patient in page_obj.object_list:
        completed_appointments = [
            appointment
            for appointment in patient.psychologist_appointments
            if appointment.status == Appointment.Status.COMPLETED
        ]

        upcoming_appointments = [
            appointment
            for appointment in patient.psychologist_appointments
            if (
                appointment.status
                in [
                    Appointment.Status.PENDING,
                    Appointment.Status.CONFIRMED,
                ]
                and appointment.availability_slot.start_time >= now
            )
        ]

        patient.last_session = (
            max(
                completed_appointments,
                key=lambda appointment: (
                    appointment.availability_slot.start_time
                ),
            )
            if completed_appointments
            else None
        )

        patient.next_session = (
            min(
                upcoming_appointments,
                key=lambda appointment: (
                    appointment.availability_slot.start_time
                ),
            )
            if upcoming_appointments
            else None
        )

        patient.is_active_patient = (
            patient.current_relationship_status
            == PatientPsychologistRelationship.Status.ACTIVE
        )

        patient.is_inactive_patient = (
            patient.current_relationship_status
            == PatientPsychologistRelationship.Status.INACTIVE
        )

        patient.is_discharged_patient = (
            patient.current_relationship_status
            == PatientPsychologistRelationship.Status.DISCHARGED
        )

    context = {
        "page_title": "Mis pacientes",
        "page_obj": page_obj,
        "query": query,
        "status_filter": status_filter,
        "filtered_patients_count": filtered_patients_count,
        "total_patients_count": total_patients_count,
        "active_patients_count": active_patients_count,
        "inactive_patients_count": inactive_patients_count,
        "discharged_patients_count": discharged_patients_count,
        "today_sessions_count": today_sessions_count,
        "completed_sessions_count": completed_sessions_count,
    }

    return render(
        request,
        "patients/psychologist_patient_list.html",
        context,
    )

@login_required
def psychologist_patient_detail(request, public_id):
    """
    Muestra el detalle de un paciente vinculado
    con el psicólogo autenticado.

    El acceso depende de la relación paciente-psicólogo
    y no de la existencia de citas.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    now = timezone.now()

    patient = get_object_or_404(
        Patient.objects
        .select_related(
            "account",
        )
        .filter(
            psychologist_relationships__psychologist__account=request.user,
        )
        .distinct(),
        public_id=public_id,
    )

    current_relationship = (
        PatientPsychologistRelationship.objects
        .filter(
            patient=patient,
            psychologist__account=request.user,
        )
        .select_related(
            "psychologist",
        )
        .order_by(
            "-started_at",
            "-id",
        )
        .first()
    )
    
    status_form = PsychologistPatientStatusForm(
        relationship=current_relationship,
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
        status=Appointment.Status.COMPLETED,
    )

    upcoming_appointments = (
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
    )

    context = {
        "page_title": "Detalle del paciente",
        "patient": patient,
        "current_relationship": current_relationship,
        "status_form": status_form,
        "upcoming_appointments": upcoming_appointments,
        "completed_appointments": completed_appointments,
    }

    return render(
        request,
        "patients/psychologist_patient_detail.html",
        context,
    )
    
@login_required
def psychologist_patient_status_update(request, public_id):
    """
    Permite al psicólogo actualizar el estado de atención
    de un paciente vinculado.

    El cambio se realiza sobre la relación paciente-psicólogo,
    sin eliminar al paciente ni deshabilitar su cuenta.
    """

    if request.user.role != Account.Role.PSYCHOLOGIST:
        return redirect("dashboard-redirect")

    relationship = get_object_or_404(
        PatientPsychologistRelationship.objects
        .select_related(
            "patient",
            "patient__account",
            "psychologist",
            "psychologist__account",
        ),
        patient__public_id=public_id,
        psychologist__account=request.user,
    )

    if request.method != "POST":
        return redirect(
            "psychologist-patient-detail",
            public_id=relationship.patient.public_id,
        )

    form = PsychologistPatientStatusForm(
        request.POST,
        relationship=relationship,
    )

    if form.is_valid():
        new_status = form.cleaned_data["status"]
        previous_status = relationship.status

        if new_status == previous_status:
            messages.info(
                request,
                (
                    "El paciente ya se encuentra en el estado "
                    f"{relationship.get_status_display().lower()}."
                ),
            )

            return redirect(
                "psychologist-patient-detail",
                public_id=relationship.patient.public_id,
            )

        relationship.status = new_status
        relationship.save()

        messages.success(
            request,
            (
                "El estado del paciente fue actualizado a "
                f"{relationship.get_status_display()}."
            ),
        )

    else:
        messages.error(
            request,
            "No fue posible actualizar el estado del paciente.",
        )

    return redirect(
        "psychologist-patient-detail",
        public_id=relationship.patient.public_id,
    )