"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.contrib.auth.views import LoginView
from django.conf.urls.static import static
from apps.accounts.forms import AccountAuthenticationForm
from apps.accounts.views import (
    admin_dashboard,
    dashboard_redirect,
    patient_dashboard,
    profile_view,
    psychologist_dashboard,
)
from apps.appointments.views import (
    patient_appointment_booking,
    patient_appointment_cancel,
    patient_appointment_confirm,
    patient_appointment_detail,
    patient_appointment_list,
    patient_appointment_reschedule,
    patient_appointment_reschedule_confirm,
    psychologist_appointment_detail,
    psychologist_appointment_list,
    psychologist_availability_slot_list,
    psychologist_availability_slot_create,
    psychologist_availability_slot_edit,
)
from apps.assignments.views import (
    patient_assignment_detail,
    patient_assignment_list,
    psychologist_assignment_create,
    psychologist_assignment_edit,
    psychologist_assignment_list,
    psychologist_assignment_general_list,
    psychologist_assignment_attachment_upload,
    psychologist_assignment_attachment_delete,
    patient_assignment_attachment_upload,
    patient_assignment_attachment_delete,
)
from apps.patients.views import (
    psychologist_patient_create,
    psychologist_patient_created,
    psychologist_patient_detail,
    psychologist_patient_list,
    psychologist_patient_status_update,
)
from apps.clinical_records.views import (
    psychologist_clinical_record_detail,
    psychologist_clinical_record_edit,
    psychologist_session_note_list,
    psychologist_session_note_manage,
)
from apps.psychologists.views import (
    admin_psychologist_account_status_update,
    admin_psychologist_create,
    admin_psychologist_created,
    admin_psychologist_detail,
    admin_psychologist_edit,
    admin_psychologist_list,
)
urlpatterns = [
    # Autenticación.
    #
    # Se declara primero la ruta personalizada de inicio de sesión
    # para utilizar el formulario que distingue las cuentas inactivas.
    path(
        "accounts/login/",
        LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=AccountAuthenticationForm,
        ),
        name="login",
    ),

    # Se conservan las demás rutas de autenticación de Django:
    # logout, cambio de contraseña y recuperación de contraseña.
    path(
        "accounts/",
        include("django.contrib.auth.urls"),
    ),

    # Dashboards.
    path(
        "dashboard/",
        dashboard_redirect,
        name="dashboard-redirect",
    ),
    path(
        "dashboard/administracion/",
        admin_dashboard,
        name="admin-dashboard",
    ),
    path(
        "dashboard/psicologo/",
        psychologist_dashboard,
        name="psychologist-dashboard",
    ),
    path(
        "dashboard/paciente/",
        patient_dashboard,
        name="patient-dashboard",
    ),
    
    # Gestión de psicólogos por el administrador.
    path(
        "administracion/psicologos/nuevo/",
        admin_psychologist_create,
        name="admin-psychologist-create",
    ),
    path(
        "administracion/psicologos/registrado/",
        admin_psychologist_created,
        name="admin-psychologist-created",
    ),
    path(
        "administracion/psicologos/",
        admin_psychologist_list,
        name="admin-psychologist-list",
    ),
    path(
        "administracion/psicologos/<int:psychologist_id>/editar/",
        admin_psychologist_edit,
        name="admin-psychologist-edit",
    ),
    path(
        "administracion/psicologos/<int:psychologist_id>/",
        admin_psychologist_detail,
        name="admin-psychologist-detail",
    ),
    path(
        "administracion/psicologos/<int:psychologist_id>/estado-cuenta/",
        admin_psychologist_account_status_update,
        name="admin-psychologist-account-status-update",
    ),

    # Perfil.
    path(
        "perfil/",
        profile_view,
        name="profile",
    ),

    # Citas del paciente.
    path(
        "mis-citas/",
        patient_appointment_list,
        name="patient-appointment-list",
    ),
    path(
        "mis-citas/agendar/",
        patient_appointment_booking,
        name="patient-appointment-booking",
    ),
    path(
        "mis-citas/agendar/<uuid:public_id>/confirmar/",
        patient_appointment_confirm,
        name="patient-appointment-confirm",
    ),
    path(
        "mis-citas/<uuid:public_id>/detalle/",
        patient_appointment_detail,
        name="patient-appointment-detail",
    ),
    path(
        "mis-citas/<uuid:public_id>/cancelar/",
        patient_appointment_cancel,
        name="patient-appointment-cancel",
    ),
    path(
        "mis-citas/<uuid:public_id>/reprogramar/",
        patient_appointment_reschedule,
        name="patient-appointment-reschedule",
    ),
    path(
        (
            "mis-citas/<uuid:public_id>/reprogramar/"
            "<uuid:slot_public_id>/confirmar/"
        ),
        patient_appointment_reschedule_confirm,
        name="patient-appointment-reschedule-confirm",
    ),

    # Agenda del psicólogo.
    path(
        "agenda/",
        psychologist_appointment_list,
        name="psychologist-appointment-list",
    ),
    path(
        "agenda/<uuid:public_id>/detalle/",
        psychologist_appointment_detail,
        name="psychologist-appointment-detail",
    ),
    path(
        "mis-cupos/",
        psychologist_availability_slot_list,
        name="psychologist-availability-slot-list",
    ),
    path(
        "mis-cupos/nuevo/",
        psychologist_availability_slot_create,
        name="psychologist-availability-slot-create",
    ),
    path(
        "mis-cupos/<int:slot_id>/editar/",
        psychologist_availability_slot_edit,
        name="psychologist-availability-slot-edit",
    ),

    # Asignaciones del paciente.
    path(
        "mis-asignaciones/",
        patient_assignment_list,
        name="patient-assignment-list",
    ),
    path(
        "mis-asignaciones/<uuid:public_id>/detalle/",
        patient_assignment_detail,
        name="patient-assignment-detail",
    ),
    path(
        "mis-asignaciones/<uuid:public_id>/adjuntar/",
        patient_assignment_attachment_upload,
        name="patient-assignment-attachment-upload",
    ),
    path(
        "mis-asignaciones/archivos/<int:attachment_id>/eliminar/",
        patient_assignment_attachment_delete,
        name="patient-assignment-attachment-delete",
    ),
    
    # Asignaciones del psicólogo.
    path(
        "notas/<uuid:note_public_id>/asignaciones/",
        psychologist_assignment_list,
        name="psychologist-assignment-list",
    ),
    path(
        "notas/<uuid:note_public_id>/asignaciones/nueva/",
        psychologist_assignment_create,
        name="psychologist-assignment-create",
    ),
    path(
        "asignaciones/<uuid:public_id>/editar/",
        psychologist_assignment_edit,
        name="psychologist-assignment-edit",
    ),
    path(
        "asignaciones/<uuid:public_id>/adjuntar/",
        psychologist_assignment_attachment_upload,
        name="psychologist-assignment-attachment-upload",
    ),
    path(
        "archivos-adjuntos/<int:attachment_id>/eliminar/",
        psychologist_assignment_attachment_delete,
        name="psychologist-assignment-attachment-delete",
    ),
    path(
        "asignaciones/",
        psychologist_assignment_general_list,
        name="psychologist-assignment-general-list",
    ),
    
    # Pacientes.
    path(
        "mis-pacientes/",
        psychologist_patient_list,
        name="psychologist-patient-list",
    ),
    path(
        "mis-pacientes/nuevo/",
        psychologist_patient_create,
        name="psychologist-patient-create",
    ),
    path(
        "mis-pacientes/nuevo/creado/",
        psychologist_patient_created,
        name="psychologist-patient-created",
    ),
    path(
        "mis-pacientes/<uuid:public_id>/detalle/",
        psychologist_patient_detail,
        name="psychologist-patient-detail",
    ),
    path(
        "mis-pacientes/<uuid:patient_public_id>/expediente/",
        psychologist_clinical_record_detail,
        name="psychologist-clinical-record-detail",
    ),
    path(
        "mis-pacientes/<uuid:patient_public_id>/expediente/editar/",
        psychologist_clinical_record_edit,
        name="psychologist-clinical-record-edit",
    ),
    path(
        "mis-pacientes/<uuid:public_id>/estado/",
        psychologist_patient_status_update,
        name="psychologist-patient-status-update",
    ),
    
    # Notas de sesiones
    # Notas de sesión del psicólogo.
    path(
        "notas-de-sesion/",
        psychologist_session_note_list,
        name="psychologist-session-note-list",
    ),
    path(
        "agenda/<uuid:appointment_public_id>/nota/",
        psychologist_session_note_manage,
        name="psychologist-session-note-manage",
    ),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )