from django.db import migrations
from django.db.models import Max, Min


def populate_patient_psychologist_relationships(
    apps,
    schema_editor,
):
    """
    Crea una relación paciente-psicólogo por cada combinación
    existente en las citas del sistema.

    La fecha inicial se toma de la primera cita registrada.
    Cuando el paciente no está activo, la fecha final se toma
    de su última cita registrada.
    """

    Appointment = apps.get_model(
        "appointments",
        "Appointment",
    )

    PatientPsychologistRelationship = apps.get_model(
        "patients",
        "PatientPsychologistRelationship",
    )

    relationships_data = (
        Appointment.objects
        .values(
            "patient_id",
            "psychologist_id",
            "patient__status",
        )
        .annotate(
            first_appointment=Min(
                "availability_slot__start_time",
            ),
            last_appointment=Max(
                "availability_slot__start_time",
            ),
        )
    )

    relationships_to_create = []

    for relationship_data in relationships_data:
        patient_status = relationship_data[
            "patient__status"
        ]

        ended_at = None

        if patient_status != "ACTIVE":
            ended_at = relationship_data[
                "last_appointment"
            ]

        relationships_to_create.append(
            PatientPsychologistRelationship(
                patient_id=relationship_data[
                    "patient_id"
                ],
                psychologist_id=relationship_data[
                    "psychologist_id"
                ],
                status=patient_status,
                started_at=relationship_data[
                    "first_appointment"
                ],
                ended_at=ended_at,
            )
        )

    PatientPsychologistRelationship.objects.bulk_create(
        relationships_to_create,
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0006_alter_patient_status_patientpsychologistrelationship'),
    ]

    operations = [
        migrations.RunPython(
            populate_patient_psychologist_relationships,
            reverse_code=migrations.RunPython.noop,
        ),
    ]