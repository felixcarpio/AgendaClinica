import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils.crypto import get_random_string
from django.core.paginator import Paginator
from django.db.models import Q
from apps.accounts.models import Account
from apps.psychologists.forms import (
    AdminPsychologistCreateForm,
    AdminPsychologistUpdateForm,
)
from apps.psychologists.models import Psychologist


logger = logging.getLogger(__name__)


@login_required
def admin_psychologist_create(request):
    """
    Permite que un administrador registre un psicólogo nuevo.

    La operación crea, dentro de una única transacción:

    - La cuenta de acceso con rol de psicólogo.
    - El perfil profesional del psicólogo.
    - Una contraseña temporal.

    Si ocurre un error durante el proceso, todos los cambios
    realizados dentro de la transacción se revierten.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    if request.method == "POST":
        form = AdminPsychologistCreateForm(
            request.POST,
        )

        if form.is_valid():
            temporary_password = get_random_string(
                length=12,
                allowed_chars=(
                    "abcdefghjkmnpqrstuvwxyz"
                    "ABCDEFGHJKMNPQRSTUVWXYZ"
                    "23456789"
                    "@#$%"
                ),
            )

            try:
                with transaction.atomic():
                    account = Account(
                        email=form.cleaned_data["email"],
                        first_name=form.cleaned_data["first_name"],
                        last_name=form.cleaned_data["last_name"],
                        role=Account.Role.PSYCHOLOGIST,
                        is_active=True,
                        is_staff=False,
                    )

                    account.set_password(
                        temporary_password,
                    )

                    account.full_clean()
                    account.save()

                    psychologist = Psychologist(
                        account=account,
                        gender=form.cleaned_data["gender"],
                        license_number=(
                            form.cleaned_data["license_number"]
                        ),
                        specialty=form.cleaned_data["specialty"],
                        professional_phone=(
                            form.cleaned_data[
                                "professional_phone"
                            ]
                        ),
                        bio=form.cleaned_data["bio"],
                        attention_mode=(
                            form.cleaned_data["attention_mode"]
                        ),
                        is_available_for_appointments=(
                            form.cleaned_data[
                                "is_available_for_appointments"
                            ]
                        ),
                    )

                    psychologist.full_clean()
                    psychologist.save()

            except IntegrityError:
                form.add_error(
                    None,
                    (
                        "No fue posible registrar al psicólogo. "
                        "El correo o el número de licencia "
                        "podrían estar siendo utilizados."
                    ),
                )

            except Exception:
                logger.exception(
                    (
                        "Error al registrar un psicólogo "
                        "desde el portal del administrador."
                    )
                )

                form.add_error(
                    None,
                    (
                        "No fue posible registrar al psicólogo. "
                        "Verifica los datos e inténtalo nuevamente."
                    ),
                )

            else:
                # Las credenciales se almacenan temporalmente
                # en la sesión para mostrarlas una sola vez.
                request.session[
                    "new_psychologist_credentials"
                ] = {
                    "psychologist_id": psychologist.id,
                    "psychologist_name": (
                        f"{account.first_name} "
                        f"{account.last_name}"
                    ),
                    "email": account.email,
                    "temporary_password": (
                        temporary_password
                    ),
                }

                messages.success(
                    request,
                    "El psicólogo fue registrado correctamente.",
                )

                return redirect(
                    "admin-psychologist-created",
                )

    else:
        form = AdminPsychologistCreateForm()

    context = {
        "page_title": "Nuevo psicólogo",
        "form": form,
    }

    return render(
        request,
        "psychologists/admin_psychologist_create.html",
        context,
    )


@login_required
def admin_psychologist_created(request):
    """
    Muestra las credenciales temporales del psicólogo
    recién registrado.

    La información se elimina de la sesión después
    de ser consultada, por lo que solo puede mostrarse
    una vez.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    credentials = request.session.pop(
        "new_psychologist_credentials",
        None,
    )

    if credentials is None:
        return redirect(
            "admin-dashboard",
        )

    context = {
        "page_title": "Psicólogo registrado",
        "credentials": credentials,
    }

    return render(
        request,
        "psychologists/admin_psychologist_created.html",
        context,
    )
    
@login_required
def admin_psychologist_list(request):
    """
    Muestra los psicólogos registrados en el sistema.

    Permite al administrador:
    - buscar por nombre, apellido, correo, licencia o especialidad;
    - filtrar según disponibilidad para recibir citas;
    - ordenar los resultados;
    - paginar el listado.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    query = request.GET.get(
        "q",
        "",
    ).strip()

    availability_filter = request.GET.get(
        "availability",
        "",
    ).strip().lower()

    ordering = request.GET.get(
        "ordering",
        "name",
    ).strip().lower()

    psychologists = (
        Psychologist.objects
        .select_related(
            "account",
        )
    )

    if query:
        psychologists = psychologists.filter(
            Q(account__first_name__icontains=query)
            | Q(account__last_name__icontains=query)
            | Q(account__email__icontains=query)
            | Q(license_number__icontains=query)
            | Q(specialty__icontains=query)
        )

    if availability_filter == "available":
        psychologists = psychologists.filter(
            is_available_for_appointments=True,
        )

    elif availability_filter == "unavailable":
        psychologists = psychologists.filter(
            is_available_for_appointments=False,
        )

    else:
        availability_filter = ""

    if ordering == "newest":
        psychologists = psychologists.order_by(
            "-created_at",
        )

    elif ordering == "oldest":
        psychologists = psychologists.order_by(
            "created_at",
        )

    elif ordering == "specialty":
        psychologists = psychologists.order_by(
            "specialty",
            "account__first_name",
            "account__last_name",
        )

    else:
        ordering = "name"

        psychologists = psychologists.order_by(
            "account__first_name",
            "account__last_name",
        )

    filtered_psychologists_count = psychologists.count()

    paginator = Paginator(
        psychologists,
        10,
    )

    page_obj = paginator.get_page(
        request.GET.get("page"),
    )

    context = {
        "page_title": "Psicólogos",
        "page_obj": page_obj,
        "query": query,
        "availability_filter": availability_filter,
        "ordering": ordering,
        "filtered_psychologists_count": (
            filtered_psychologists_count
        ),
    }

    return render(
        request,
        "psychologists/admin_psychologist_list.html",
        context,
    )
    
@login_required
def admin_psychologist_edit(request, psychologist_id):
    """
    Permite al administrador actualizar la información
    personal y profesional de un psicólogo registrado.

    No modifica el correo, la contraseña ni el rol de la cuenta.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    psychologist = get_object_or_404(
        Psychologist.objects.select_related(
            "account",
        ),
        id=psychologist_id,
    )

    if request.method == "POST":
        form = AdminPsychologistUpdateForm(
            request.POST,
            instance=psychologist,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()

            except IntegrityError:
                form.add_error(
                    "license_number",
                    (
                        "No fue posible guardar los cambios. "
                        "El número de licencia podría estar "
                        "siendo utilizado."
                    ),
                )

            except Exception:
                logger.exception(
                    (
                        "Error al actualizar un psicólogo "
                        "desde el portal del administrador."
                    )
                )

                form.add_error(
                    None,
                    (
                        "No fue posible actualizar al psicólogo. "
                        "Verifica los datos e inténtalo nuevamente."
                    ),
                )

            else:
                messages.success(
                    request,
                    "La información del psicólogo fue actualizada correctamente.",
                )

                return redirect(
                    "admin-psychologist-list",
                )

    else:
        form = AdminPsychologistUpdateForm(
            instance=psychologist,
        )

    context = {
        "page_title": "Editar psicólogo",
        "psychologist": psychologist,
        "form": form,
    }

    return render(
        request,
        "psychologists/admin_psychologist_edit.html",
        context,
    )
    
@login_required
def admin_psychologist_detail(request, psychologist_id):
    """
    Muestra la información completa de un psicólogo
    para consulta por parte del administrador.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    psychologist = get_object_or_404(
        Psychologist.objects.select_related(
            "account",
        ),
        id=psychologist_id,
    )

    context = {
        "page_title": "Detalle del psicólogo",
        "psychologist": psychologist,
    }

    return render(
        request,
        "psychologists/admin_psychologist_detail.html",
        context,
    )
    
@login_required
@require_POST
def admin_psychologist_account_status_update(
    request,
    psychologist_id,
):
    """
    Activa o desactiva la cuenta asociada a un psicólogo.

    Esta acción afecta únicamente el acceso al sistema.
    No modifica su disponibilidad para recibir citas.
    """

    if request.user.role != Account.Role.ADMIN:
        return redirect("dashboard-redirect")

    psychologist = get_object_or_404(
        Psychologist.objects.select_related(
            "account",
        ),
        id=psychologist_id,
    )

    requested_status = request.POST.get(
        "status",
        "",
    ).strip().lower()

    if requested_status not in {
        "activate",
        "deactivate",
    }:
        messages.error(
            request,
            "La acción solicitada no es válida.",
        )

        return redirect(
            "admin-psychologist-detail",
            psychologist_id=psychologist.id,
        )

    account = psychologist.account
    should_be_active = requested_status == "activate"

    if account.is_active == should_be_active:
        if should_be_active:
            messages.info(
                request,
                "La cuenta del psicólogo ya se encuentra activa.",
            )
        else:
            messages.info(
                request,
                "La cuenta del psicólogo ya se encuentra inactiva.",
            )

        return redirect(
            "admin-psychologist-detail",
            psychologist_id=psychologist.id,
        )

    try:
        with transaction.atomic():
            account.is_active = should_be_active

            account.save(
                update_fields=[
                    "is_active",
                ]
            )

    except Exception:
        logger.exception(
            (
                "Error al actualizar el estado de la cuenta "
                "de un psicólogo."
            )
        )

        messages.error(
            request,
            (
                "No fue posible actualizar el estado de la cuenta. "
                "Inténtalo nuevamente."
            ),
        )

    else:
        if should_be_active:
            messages.success(
                request,
                "La cuenta del psicólogo fue activada correctamente.",
            )
        else:
            messages.success(
                request,
                "La cuenta del psicólogo fue desactivada correctamente.",
            )

    return redirect(
        "admin-psychologist-detail",
        psychologist_id=psychologist.id,
    )