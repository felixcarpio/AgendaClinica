from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def dashboard_redirect(request):
    """
    Redirige al usuario autenticado hacia el dashboard
    correspondiente según el rol almacenado en su cuenta.
    """

    user = request.user

    if user.role == "ADMIN":
        return redirect("admin-dashboard")

    if user.role == "PSYCHOLOGIST":
        return redirect("psychologist-dashboard")

    if user.role == "PATIENT":
        return redirect("patient-dashboard")

    # Si la cuenta no tiene un rol válido, se cierra el flujo
    # enviando nuevamente al inicio de sesión.
    return redirect("login")


@login_required
def admin_dashboard(request):
    """
    Muestra el dashboard exclusivo para usuarios administradores.
    """

    if request.user.role != "ADMIN":
        return redirect("dashboard-redirect")

    context = {
        "page_title": "Panel de administración",
    }

    return render(
        request,
        "dashboard/admin_dashboard.html",
        context,
    )


@login_required
def psychologist_dashboard(request):
    """
    Muestra el dashboard exclusivo para psicólogos.
    """

    if request.user.role != "PSYCHOLOGIST":
        return redirect("dashboard-redirect")

    context = {
        "page_title": "Panel del psicólogo",
    }

    return render(
        request,
        "dashboard/psychologist_dashboard.html",
        context,
    )


@login_required
def patient_dashboard(request):
    """
    Muestra el dashboard exclusivo para pacientes.
    """

    if request.user.role != "PATIENT":
        return redirect("dashboard-redirect")

    context = {
        "page_title": "Panel del paciente",
    }

    return render(
        request,
        "dashboard/patient_dashboard.html",
        context,
    )
    
@login_required
def profile_view(request):
    """
    Muestra la información básica de la cuenta
    del usuario autenticado.
    """

    context = {
        "page_title": "Mi perfil",
    }

    return render(
        request,
        "accounts/profile.html",
        context,
    )