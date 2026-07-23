from django.utils import timezone

from .models import Appointment


def complete_finished_confirmed_appointments():
    """
    Cambia automáticamente a completadas las citas confirmadas
    cuya hora de finalización ya haya pasado.

    Solo se modifican citas en estado CONFIRMED.
    Las citas pendientes, canceladas o ya completadas
    permanecen sin cambios.

    Returns:
        int: cantidad de citas actualizadas.
    """

    now = timezone.now()

    return (
        Appointment.objects
        .filter(
            status=Appointment.Status.CONFIRMED,
            availability_slot__end_time__lte=now,
        )
        .update(
            status=Appointment.Status.COMPLETED,
            updated_at=now,
        )
    )