"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import include
from django.views.generic import TemplateView
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
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "accounts/",
        include("django.contrib.auth.urls"),
    ),
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
    path(
        "perfil/",
        profile_view,
        name="profile",
    ),
    path(
        "mis-citas/",
        patient_appointment_list,
        name="patient-appointment-list",
    ),
    path(
        "mis-citas/<uuid:public_id>/detalle/",
        patient_appointment_detail,
        name="patient-appointment-detail",
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
        "mis-citas/<uuid:public_id>/cancelar/",
        patient_appointment_cancel,
        name="patient-appointment-cancel",
    ),
]