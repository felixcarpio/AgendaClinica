from django.urls import path

from apps.patients import views


urlpatterns = [
    path(
        "",
        views.psychologist_patient_list,
        name="psychologist-patient-list",
    ),
    path(
        "nuevo/",
        views.psychologist_patient_create,
        name="psychologist-patient-create",
    ),
    path(
        "nuevo/creado/",
        views.psychologist_patient_created,
        name="psychologist-patient-created",
    ),
    path(
        "<uuid:public_id>/",
        views.psychologist_patient_detail,
        name="psychologist-patient-detail",
    ),
]