import calendar
from datetime import date
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from apps.appointments.forms import (
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

    # Citas completadas, canceladas o cuya fecha ya pasó.
    appointment_history = (
        appointments
        .filter(
            Q(
                status__in=[
                    Appointment.Status.COMPLETED,
                    Appointment.Status.CANCELLED,
                ]
            )
            | Q(availability_slot__start_time__lt=now)
        )
        .exclude(
            status__in=[
                Appointment.Status.PENDING,
                Appointment.Status.CONFIRMED,
            ],
            availability_slot__start_time__gte=now,
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
                status="AVAILABLE",
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
                    locked_slot.status
                    != AvailabilitySlot.Status.AVAILABLE
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
    if slot.status != AvailabilitySlot.Status.AVAILABLE:
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