from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import Account
from .models import Patient


@receiver(post_save, sender=Account)
def create_patient_profile(sender, instance, created, **kwargs):
    if created and instance.role == Account.Role.PATIENT:
        Patient.objects.get_or_create(account=instance)