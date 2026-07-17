import calendar
from datetime import date
from django.utils import timezone
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from apps.appointments.forms import (
    PatientAppointmentCancellationForm,
    PatientAppointmentConfirmationForm,
)
from apps.patients.models import Patient
from apps.appointments.models import Appointment
from apps.appointments.models import AvailabilitySlot
from apps.psychologists.models import Psychologist


@login_required
def patient_appointment_list(request):
    """
    Muestra las citas del paciente autenticado, separadas en:

    - próximas citas;
    - historial de citas.

    El paciente únicamente puede consultar sus propios registros.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    now = timezone.now()

    appointments = (
        Appointment.objects
        .filter(patient__account=request.user)
        .select_related(
            "patient",
            "psychologist",
            "psychologist__account",
            "availability_slot",
        )
    )

    # Citas pendientes o confirmadas cuya fecha todavía no ha pasado.
    upcoming_appointments = (
        appointments
        .filter(
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.CONFIRMED,
            ],
            availability_slot__start_time__gte=now,
        )
        .order_by("availability_slot__start_time")
    )

    # Historial visible para el paciente:
    # únicamente citas completadas.
    appointment_history = (
        appointments
        .filter(
            status=Appointment.Status.COMPLETED,
        )
        .order_by("-availability_slot__start_time")
    )

    context = {
        "page_title": "Mis citas",
        "upcoming_appointments": upcoming_appointments,
        "appointment_history": appointment_history,
    }

    return render(
        request,
        "appointments/patient_appointment_list.html",
        context,
    )


@login_required
def patient_appointment_detail(request, public_id):
    """
    Muestra el detalle de una cita perteneciente
    al paciente autenticado.

    La cita se identifica mediante un UUID público
    y el paciente solo puede consultar sus propias citas.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "patient",
            "psychologist",
            "availability_slot",
        ),
        public_id=public_id,
        patient__account=request.user,
    )

    context = {
        "page_title": "Detalle de la cita",
        "appointment": appointment,
    }

    return render(
        request,
        "appointments/patient_appointment_detail.html",
        context,
    )
    
@login_required
def patient_appointment_booking(request):
    """
    Muestra el calendario de agendamiento para el paciente.

    Permite:
    - navegar entre meses;
    - seleccionar una fecha;
    - filtrar por psicólogo;
    - consultar slots disponibles.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    today = date.today()

    # Fecha seleccionada desde la URL.
    selected_date_param = request.GET.get("date")
    selected_date = (
        parse_date(selected_date_param)
        if selected_date_param
        else today
    )

    if selected_date is None:
        selected_date = today

    # Mes mostrado en el calendario.
    try:
        displayed_year = int(
            request.GET.get("year", selected_date.year)
        )
        displayed_month = int(
            request.GET.get("month", selected_date.month)
        )

        if displayed_month < 1 or displayed_month > 12:
            raise ValueError

    except (TypeError, ValueError):
        displayed_year = today.year
        displayed_month = today.month

    selected_psychologist_id = request.GET.get("psychologist")

    psychologists = (
        Psychologist.objects
        .select_related("account")
        .all()
        .order_by(
            "account__first_name",
            "account__last_name",
        )
    )

    slots = AvailabilitySlot.objects.none()

    if selected_date:
        slots = (
            AvailabilitySlot.objects
            .select_related(
                "psychologist",
                "psychologist__account",
            )
            .filter(
                start_time__date=selected_date,
                start_time__gt=timezone.now(),
                status=AvailabilitySlot.Status.AVAILABLE,
            )
            .order_by(
                "psychologist__account__first_name",
                "start_time",
            )
        )

        if selected_psychologist_id:
            slots = slots.filter(
                psychologist_id=selected_psychologist_id
            )

    # Construye las semanas del calendario.
    month_calendar = calendar.Calendar(
        firstweekday=calendar.MONDAY
    )

    calendar_weeks = month_calendar.monthdatescalendar(
        displayed_year,
        displayed_month,
    )

    # Mes anterior.
    if displayed_month == 1:
        previous_month = 12
        previous_year = displayed_year - 1
    else:
        previous_month = displayed_month - 1
        previous_year = displayed_year

    # Mes siguiente.
    if displayed_month == 12:
        next_month = 1
        next_year = displayed_year + 1
    else:
        next_month = displayed_month + 1
        next_year = displayed_year

    month_names = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre",
    }

    context = {
        "page_title": "Agendar nueva cita",
        "today": today,
        "selected_date": selected_date,
        "selected_psychologist_id": selected_psychologist_id,
        "psychologists": psychologists,
        "slots": slots,

        # Información del calendario.
        "calendar_weeks": calendar_weeks,
        "displayed_month": displayed_month,
        "displayed_year": displayed_year,
        "displayed_month_name": month_names[displayed_month],

        # Navegación mensual.
        "previous_month": previous_month,
        "previous_year": previous_year,
        "next_month": next_month,
        "next_year": next_year,
    }

    return render(
        request,
        "appointments/patient_appointment_booking.html",
        context,
    )
    
@login_required
def patient_appointment_confirm(request, public_id):
    """
    Muestra y procesa la confirmación de una cita.

    La reserva se realiza dentro de una transacción para evitar
    que dos pacientes confirmen el mismo horario simultáneamente.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    patient = get_object_or_404(
        Patient,
        account=request.user,
    )

    slot = get_object_or_404(
        AvailabilitySlot.objects.select_related(
            "psychologist",
            "psychologist__account",
        ),
        public_id=public_id,
    )

    if request.method == "POST":
        form = PatientAppointmentConfirmationForm(
            request.POST
        )

        if form.is_valid():
            with transaction.atomic():
                # Se vuelve a consultar bloqueando la fila
                # mientras se procesa la reserva.
                locked_slot = get_object_or_404(
                    AvailabilitySlot.objects
                    .select_for_update()
                    .select_related(
                        "psychologist",
                        "psychologist__account",
                    ),
                    public_id=public_id,
                )

                if (
                    locked_slot.status != AvailabilitySlot.Status.AVAILABLE
                    or locked_slot.start_time <= timezone.now()
                ):
                    messages.error(
                        request,
                        (
                            "El horario seleccionado ya fue reservado "
                            "por otra persona."
                        ),
                    )

                    return redirect(
                        "patient-appointment-booking"
                    )

                appointment = Appointment(
                    patient=patient,
                    psychologist=locked_slot.psychologist,
                    availability_slot=locked_slot,
                    reason=form.cleaned_data["reason"],
                )

                # clean() ejecuta las validaciones del modelo
                # antes de guardar la cita.
                appointment.full_clean()
                appointment.save()

            messages.success(
                request,
                "Tu cita se agendó correctamente.",
            )

            return redirect(
                "patient-appointment-booking"
            )

    else:
        form = PatientAppointmentConfirmationForm()

    # También se valida al cargar la pantalla.
    if (slot.status != AvailabilitySlot.Status.AVAILABLE or slot.start_time <= timezone.now()):
        messages.error(
            request,
            "El horario seleccionado ya no está disponible.",
        )

        return redirect(
            "patient-appointment-booking"
        )

    context = {
        "page_title": "Confirmar cita",
        "slot": slot,
        "form": form,
    }

    return render(
        request,
        "appointments/patient_appointment_confirm.html",
        context,
    )
    
@login_required
def patient_appointment_cancel(request, public_id):
    """
    Permite al paciente cancelar una cita propia
    que todavía esté pendiente o confirmada.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "patient",
            "psychologist",
            "availability_slot",
        ),
        public_id=public_id,
        patient__account=request.user,
    )

    allowed_statuses = {
        Appointment.Status.PENDING,
        Appointment.Status.CONFIRMED,
    }

    if appointment.status not in allowed_statuses:
        messages.error(
            request,
            "Esta cita ya no puede ser cancelada.",
        )
        return redirect(
            "patient-appointment-detail",
            public_id=appointment.public_id,
        )

    if request.method == "POST":
        form = PatientAppointmentCancellationForm(
            request.POST
        )

        if form.is_valid():
            appointment.status = Appointment.Status.CANCELLED
            appointment.cancelled_reason = (
                form.cleaned_data["cancelled_reason"]
            )

            appointment.full_clean()
            appointment.save()

            messages.success(
                request,
                "La cita fue cancelada correctamente.",
            )

            return redirect("patient-appointment-list")

    else:
        form = PatientAppointmentCancellationForm()

    context = {
        "page_title": "Cancelar cita",
        "appointment": appointment,
        "form": form,
    }

    return render(
        request,
        "appointments/patient_appointment_cancel.html",
        context,
    )
    
@login_required
def patient_appointment_reschedule(request, public_id):
    """
    Permite al paciente seleccionar una nueva fecha,
    un psicólogo y un cupo disponible para reprogramar
    una cita propia pendiente o confirmada.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "patient",
            "psychologist",
            "psychologist__account",
            "availability_slot",
        ),
        public_id=public_id,
        patient__account=request.user,
    )

    allowed_statuses = {
        Appointment.Status.PENDING,
        Appointment.Status.CONFIRMED,
    }

    if appointment.status not in allowed_statuses:
        messages.error(
            request,
            "Esta cita ya no puede ser reprogramada.",
        )

        return redirect(
            "patient-appointment-detail",
            public_id=appointment.public_id,
        )

    today = timezone.localdate()

    selected_date_value = request.GET.get("date")
    selected_date = parse_date(selected_date_value or "")

    if not selected_date:
        selected_date = today

    try:
        displayed_year = int(
            request.GET.get("year", selected_date.year)
        )
        displayed_month = int(
            request.GET.get("month", selected_date.month)
        )
    except (TypeError, ValueError):
        displayed_year = selected_date.year
        displayed_month = selected_date.month

    # Evita valores de mes inválidos.
    if displayed_month < 1 or displayed_month > 12:
        displayed_year = today.year
        displayed_month = today.month

    selected_psychologist_id = request.GET.get("psychologist")

    # La primera vez se selecciona automáticamente
    # el psicólogo actual de la cita.
    if not selected_psychologist_id:
        selected_psychologist_id = str(
            appointment.psychologist_id
        )

    psychologists = Psychologist.objects.select_related(
        "account"
    ).order_by(
        "account__first_name",
        "account__last_name",
    )

    available_slots = AvailabilitySlot.objects.filter(
        start_time__date=selected_date,
        status=AvailabilitySlot.Status.AVAILABLE,
        start_time__gte=timezone.now(),
    ).select_related(
        "psychologist",
        "psychologist__account",
    ).order_by(
        "start_time"
    )

    if selected_psychologist_id:
        available_slots = available_slots.filter(
            psychologist_id=selected_psychologist_id
        )

    month_calendar = calendar.Calendar(
        firstweekday=0
    )

    calendar_weeks = month_calendar.monthdatescalendar(
        displayed_year,
        displayed_month,
    )

    # Mes anterior.
    if displayed_month == 1:
        previous_month = 12
        previous_year = displayed_year - 1
    else:
        previous_month = displayed_month - 1
        previous_year = displayed_year

    # Mes siguiente.
    if displayed_month == 12:
        next_month = 1
        next_year = displayed_year + 1
    else:
        next_month = displayed_month + 1
        next_year = displayed_year

    month_names = {
        1: "Enero",
        2: "Febrero",
        3: "Marzo",
        4: "Abril",
        5: "Mayo",
        6: "Junio",
        7: "Julio",
        8: "Agosto",
        9: "Septiembre",
        10: "Octubre",
        11: "Noviembre",
        12: "Diciembre",
    }

    context = {
        "page_title": "Reprogramar cita",
        "appointment": appointment,
        "psychologists": psychologists,
        "selected_psychologist_id": str(
            selected_psychologist_id
        ),
        "selected_date": selected_date,
        "available_slots": available_slots,
        "calendar_weeks": calendar_weeks,
        "displayed_year": displayed_year,
        "displayed_month": displayed_month,
        "displayed_month_name": month_names[
            displayed_month
        ],
        "previous_month": previous_month,
        "previous_year": previous_year,
        "next_month": next_month,
        "next_year": next_year,
        "today": today,
    }

    return render(
        request,
        "appointments/patient_appointment_reschedule.html",
        context,
    )
    
@login_required
def patient_appointment_reschedule_confirm(
    request,
    public_id,
    slot_public_id,
):
    """
    Muestra y procesa la confirmación de un nuevo horario
    para una cita pendiente o confirmada del paciente.

    El nuevo cupo debe:
    - continuar disponible;
    - no haber alcanzado su hora de inicio;
    - permanecer disponible dentro de la transacción.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    allowed_statuses = {
        Appointment.Status.PENDING,
        Appointment.Status.CONFIRMED,
    }

    appointment = get_object_or_404(
        Appointment.objects.select_related(
            "patient",
            "psychologist",
            "psychologist__account",
            "availability_slot",
        ),
        public_id=public_id,
        patient__account=request.user,
    )

    # Solo las citas activas pueden reprogramarse.
    if appointment.status not in allowed_statuses:
        messages.error(
            request,
            "Esta cita ya no puede ser reprogramada.",
        )

        return redirect(
            "patient-appointment-detail",
            public_id=appointment.public_id,
        )

    new_slot = get_object_or_404(
        AvailabilitySlot.objects.select_related(
            "psychologist",
            "psychologist__account",
        ),
        public_id=slot_public_id,
    )

    # Validación inicial al cargar la pantalla.
    #
    # Aunque el cupo esté marcado como AVAILABLE, no debe utilizarse
    # si su hora de inicio ya pasó.
    if (
        new_slot.status != AvailabilitySlot.Status.AVAILABLE
        or new_slot.start_time <= timezone.now()
    ):
        messages.error(
            request,
            "El horario seleccionado ya no está disponible.",
        )

        return redirect(
            "patient-appointment-reschedule",
            public_id=appointment.public_id,
        )

    if request.method == "POST":
        try:
            with transaction.atomic():
                # Bloquea la cita para evitar que cambie mientras
                # se procesa la reprogramación.
                locked_appointment = (
                    Appointment.objects
                    .select_for_update()
                    .select_related(
                        "patient",
                        "psychologist",
                        "availability_slot",
                    )
                    .get(
                        pk=appointment.pk,
                        patient__account=request.user,
                    )
                )

                # Bloquea el nuevo cupo para impedir que otro paciente
                # lo reserve simultáneamente.
                locked_new_slot = (
                    AvailabilitySlot.objects
                    .select_for_update()
                    .select_related("psychologist")
                    .get(pk=new_slot.pk)
                )

                # Se vuelve a validar el estado de la cita dentro
                # de la transacción.
                if locked_appointment.status not in allowed_statuses:
                    messages.error(
                        request,
                        "Esta cita ya no puede ser reprogramada.",
                    )

                    return redirect(
                        "patient-appointment-detail",
                        public_id=locked_appointment.public_id,
                    )

                # Se vuelve a validar el cupo después de bloquearlo.
                #
                # Esto cubre dos posibles casos:
                # - otra persona reservó el cupo;
                # - la hora del cupo pasó mientras la pantalla
                #   de confirmación permanecía abierta.
                if (
                    locked_new_slot.status
                    != AvailabilitySlot.Status.AVAILABLE
                    or locked_new_slot.start_time <= timezone.now()
                ):
                    messages.error(
                        request,
                        (
                            "El horario seleccionado ya no está "
                            "disponible."
                        ),
                    )

                    return redirect(
                        "patient-appointment-reschedule",
                        public_id=locked_appointment.public_id,
                    )

                # El psicólogo debe coincidir siempre con el propietario
                # del nuevo cupo seleccionado.
                locked_appointment.psychologist = (
                    locked_new_slot.psychologist
                )

                locked_appointment.availability_slot = (
                    locked_new_slot
                )

                # Una cita reprogramada vuelve a quedar pendiente.
                locked_appointment.status = (
                    Appointment.Status.PENDING
                )

                # El modelo valida el cambio, libera el cupo anterior
                # y reserva el nuevo.
                locked_appointment.save()

        except ValidationError:
            messages.error(
                request,
                (
                    "No fue posible reprogramar la cita. "
                    "Verifica que el nuevo horario no se cruce "
                    "con otra cita activa."
                ),
            )

            return redirect(
                "patient-appointment-reschedule",
                public_id=appointment.public_id,
            )

        messages.success(
            request,
            "La cita fue reprogramada correctamente.",
        )

        return redirect(
            "patient-appointment-detail",
            public_id=appointment.public_id,
        )

    context = {
        "page_title": "Confirmar reprogramación",
        "appointment": appointment,
        "new_slot": new_slot,
    }

    return render(
        request,
        "appointments/patient_appointment_reschedule_confirm.html",
        context,
    )