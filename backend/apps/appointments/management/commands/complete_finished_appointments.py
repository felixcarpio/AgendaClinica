from django.core.management.base import BaseCommand

from apps.appointments.services import (
    complete_finished_confirmed_appointments,
)


class Command(BaseCommand):
    """
    Completa citas confirmadas cuya hora de finalización ya pasó.
    """

    help = (
        "Cambia a completadas las citas confirmadas "
        "cuya hora de finalización ya pasó."
    )

    def handle(self, *args, **options):
        updated_count = (
            complete_finished_confirmed_appointments()
        )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"Proceso finalizado. "
                    f"Citas actualizadas: {updated_count}."
                )
            )
        )