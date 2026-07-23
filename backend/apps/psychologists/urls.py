from django.urls import path

from apps.psychologists import views


urlpatterns = [
    path(
        "administracion/psicologos/nuevo/",
        views.admin_psychologist_create,
        name="admin-psychologist-create",
    ),
    path(
        "administracion/psicologos/registrado/",
        views.admin_psychologist_created,
        name="admin-psychologist-created",
    ),
]