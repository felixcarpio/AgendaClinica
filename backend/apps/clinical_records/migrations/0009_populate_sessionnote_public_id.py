import uuid

from django.db import migrations


def populate_sessionnote_public_id(apps, schema_editor):
    """
    Asigna un UUID público a cada nota de sesión existente
    que todavía no tenga uno.
    """

    SessionNote = apps.get_model(
        "clinical_records",
        "SessionNote",
    )

    for note in SessionNote.objects.filter(public_id__isnull=True):
        note.public_id = uuid.uuid4()
        note.save(
            update_fields=["public_id"],
        )


def reverse_sessionnote_public_id(apps, schema_editor):
    """
    Elimina los UUID asignados al revertir la migración.
    """

    SessionNote = apps.get_model(
        "clinical_records",
        "SessionNote",
    )

    SessionNote.objects.update(
        public_id=None,
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            "clinical_records",
            "0008_sessionnote_public_id",
        ),
    ]

    operations = [
        migrations.RunPython(
            populate_sessionnote_public_id,
            reverse_sessionnote_public_id,
        ),
    ]