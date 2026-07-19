import uuid

from django.db import migrations


def populate_patient_public_id(apps, schema_editor):
    """
    Asigna un UUID público a cada paciente existente
    que todavía no tenga uno.
    """

    Patient = apps.get_model("patients", "Patient")

    for patient in Patient.objects.filter(public_id__isnull=True):
        patient.public_id = uuid.uuid4()
        patient.save(
            update_fields=["public_id"],
        )


def reverse_patient_public_id(apps, schema_editor):
    """
    Permite revertir la migración eliminando los UUID asignados.
    """

    Patient = apps.get_model("patients", "Patient")

    Patient.objects.update(
        public_id=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            "patients",
            "0002_patient_public_id",
        ),
    ]

    operations = [
        migrations.RunPython(
            populate_patient_public_id,
            reverse_patient_public_id,
        ),
    ]