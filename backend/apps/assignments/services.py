from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Assignment


@transaction.atomic
def start_assignment(assignment: Assignment) -> Assignment:
    """
    Cambia una asignación pendiente al estado EN PROGRESO.

    Esta operación podrá ser utilizada por el paciente.
    """

    if assignment.status != Assignment.Status.PENDING:
        raise ValidationError(
            "Solo una asignación pendiente puede pasar a en progreso."
        )

    assignment.status = Assignment.Status.IN_PROGRESS
    assignment.save(update_fields=[
        "status",
        "is_visible",
        "completed_at",
        "updated_at",
    ])

    return assignment


@transaction.atomic
def complete_assignment(assignment: Assignment) -> Assignment:
    """
    Marca como completada una asignación pendiente o en progreso.

    Esta operación podrá ser utilizada por el paciente.
    """

    allowed_statuses = {
        Assignment.Status.PENDING,
        Assignment.Status.IN_PROGRESS,
    }

    if assignment.status not in allowed_statuses:
        raise ValidationError(
            "Solo una asignación pendiente o en progreso puede completarse."
        )

    assignment.status = Assignment.Status.COMPLETED
    assignment.save(update_fields=[
        "status",
        "is_visible",
        "completed_at",
        "updated_at",
    ])

    return assignment


@transaction.atomic
def cancel_assignment(assignment: Assignment) -> Assignment:
    """
    Cancela una asignación y la oculta del portal del paciente.

    Esta operación deberá estar disponible únicamente para el psicólogo.
    """

    if assignment.status == Assignment.Status.CANCELLED:
        raise ValidationError(
            "La asignación ya se encuentra cancelada."
        )

    assignment.status = Assignment.Status.CANCELLED
    assignment.save(update_fields=[
        "status",
        "is_visible",
        "completed_at",
        "updated_at",
    ])

    return assignment


@transaction.atomic
def reopen_assignment(assignment: Assignment) -> Assignment:
    """
    Reactiva una asignación completada o cancelada.

    Esta operación deberá estar disponible únicamente para el psicólogo.
    La asignación vuelve al estado PENDIENTE.
    """

    allowed_statuses = {
        Assignment.Status.COMPLETED,
        Assignment.Status.CANCELLED,
    }

    if assignment.status not in allowed_statuses:
        raise ValidationError(
            "Solo una asignación completada o cancelada puede reabrirse."
        )

    assignment.status = Assignment.Status.PENDING
    assignment.save(update_fields=[
        "status",
        "is_visible",
        "completed_at",
        "updated_at",
    ])

    return assignment