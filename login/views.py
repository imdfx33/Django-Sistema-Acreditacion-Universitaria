# login/views.py

import os
import mimetypes
import requests
import tempfile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.mail import send_mail
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_POST

from googleapiclient.http import MediaIoBaseUpload

from .forms import (
    AvatarUploadForm, LoginForm, ProfileForm,
    RegisterStep1Form, VerifyCodeForm
)
from .google_service import _drive_service
from .models import Rol, User


# ---------------------------------------------------------------------
#  Utilidades
# ---------------------------------------------------------------------

def _build_avatar_url(file_id: str) -> str:
    """URL pública directa para descargar el archivo de Drive."""
    return f"https://drive.google.com/uc?export=media&id={file_id}"


@cache_page(60 * 5)  # cache 5 minutos
def avatar_proxy(request, file_id):
    """
    Sirve la imagen subida a Drive a través de este endpoint.
    Evita problemas de CORS o de enlace roto.
    """
    url = _build_avatar_url(file_id)
    resp = requests.get(url, stream=True)
    if resp.status_code != 200:
        raise Http404("Avatar no encontrado")
    content_type = resp.headers.get("Content-Type", "image/png")
    return HttpResponse(resp.content, content_type=content_type)


# ---------------------------------------------------------------------
#  Registro – paso 1
# ---------------------------------------------------------------------
def register_start(request):
    form = RegisterStep1Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.enviar_codigo(request)
        messages.info(
            request,
            "Enviamos un código a tu Gmail. Escríbelo para completar el registro."
        )
        return redirect("register_verify")
    return render(request, "login/register_start.html", {"form": form})


# ---------------------------------------------------------------------
#  Registro – paso 2
# ---------------------------------------------------------------------
def register_verify(request):
    pending = request.session.get("pending_user")
    if not pending:
        return redirect("register_start")

    form = VerifyCodeForm(
        request.POST or None,
        email=pending["email"],
        session=request.session,
    )
    if request.method == "POST" and form.is_valid():
        User.objects.create_user(
            cedula=pending["cedula"],
            email=pending["email"],
            password=pending["password"],
            first_name=pending["first_name"],
            last_name=pending["last_name"],
        )
        messages.success(
            request,
            "Cuenta creada. Espera a que un administrador la active."
        )
        for k in ("pending_user", f"codigo_{pending['email']}"):
            request.session.pop(k, None)
        return redirect("login")

    return render(
        request,
        "login/register_verify.html",
        {"form": form, "email": pending["email"]},
    )


# ---------------------------------------------------------------------
#  Login / Logout
# ---------------------------------------------------------------------
def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.cleaned_data["user"]
        login(request, user)
        messages.success(request, f"¡Bienvenido {user.first_name}!")
        return redirect("home")
    return render(request, "login/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


# ---------------------------------------------------------------------
#  Perfil
# ---------------------------------------------------------------------
@login_required
def profile_view(request):
    """
    Si el usuario tiene avatar_drive_id, apunta al proxy;
    si no, muestra un avatar por defecto.
    """
    user = request.user
    if user.avatar_drive_id:
        avatar_url = reverse('avatar_proxy', kwargs={'file_id': user.avatar_drive_id})
    else:
        avatar_url = static("core/img/default-avatar.png")

    return render(request, "login/profile.html", {
        "user": user,
        "avatar_url": avatar_url,
    })


@login_required
def update_profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect("profile")
    return render(request, "login/edit_profile.html", {"form": form})


# ---------------------------------------------------------------------
#  Subir avatar
# ---------------------------------------------------------------------
def upload_avatar(request):
    form = AvatarUploadForm(request.POST or None,
                             request.FILES or None)

    if request.method == "POST" and form.is_valid():
        user = request.user
        uploaded = request.FILES['avatar']

        # 1) Borra anterior en Drive
        if user.avatar_drive_id:
            try:
                _drive_service().files().delete(
                    fileId=user.avatar_drive_id
                ).execute()
            except:
                pass

        # 2) Graba en archivo temporal fuera del repo
        suffix = os.path.splitext(uploaded.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in uploaded.chunks():
                tmp.write(chunk)
            tmp.flush()
            temp_path = tmp.name

        # 3) Súbelo a Drive
        drive = _drive_service()
        meta = {
            "name": f"{user.cedula}_{uploaded.name}",
            "parents": [settings.AVATARS_DRIVE_FOLDER_ID],
        }
        with open(temp_path, 'rb') as fh:
            media = MediaIoBaseUpload(
                fh,
                mimetype=uploaded.content_type or mimetypes.guess_type(temp_path)[0],
                resumable=False
            )
            gfile = drive.files().create(
                body=meta, media_body=media, fields="id"
            ).execute()

        # 4) Limpia el temporal
        os.remove(temp_path)

        # 5) Hazlo público y guarda sólo los campos Drive
        drive.permissions().create(
            fileId=gfile['id'],
            body={'role':'reader','type':'anyone'},
            fields='id'
        ).execute()

        user.avatar_drive_id   = gfile['id']
        user.avatar_drive_link = _build_avatar_url(gfile['id'])
        # ¡no tocamos user.avatar ni MEDIA_ROOT!
        user.save(update_fields=['avatar_drive_id','avatar_drive_link'])

        messages.success(request, "Avatar subido correctamente.")
        return redirect('profile')

    return render(request, 'login/upload_avatar.html', {'form': form})


# ---------------------------------------------------------------------
#  Eliminar avatar
# ---------------------------------------------------------------------
@login_required
@require_POST
def delete_avatar(request):
    user = request.user
    if user.avatar_drive_id:
        try:
            _drive_service().files().delete(fileId=user.avatar_drive_id).execute()
        except Exception:
            pass
    if user.avatar:
        user.avatar.delete(save=False)

    user.avatar = None
    user.avatar_drive_id = None
    user.avatar_drive_link = None
    user.save(update_fields=["avatar", "avatar_drive_id", "avatar_drive_link"])
    messages.success(request, "Avatar eliminado correctamente.")
    return redirect("profile")


# ---------------------------------------------------------------------
#  Panel de usuarios (para admins)
# ---------------------------------------------------------------------
def _es_admin(u):
    return u.is_authenticated and (
        u.is_superuser or u.rol in (Rol.SUPERADMIN, Rol.MINIADMIN)
    )


@login_required
@user_passes_test(_es_admin, login_url="login")
def usuarios_panel(request):
    usuarios = User.objects.all()
    if request.method == "POST":
        pk = request.POST.get("pk")
        u = get_object_or_404(User, pk=pk)
        u.is_active = not u.is_active
        u.save()
    return render(request, "login/usuarios_panel.html", {"usuarios": usuarios})


# ---------------------------------------------------------------------
#  Gestión de cuentas  (mini-admin)
# ---------------------------------------------------------------------
def _is_admin_or_mini(user):
    return user.is_authenticated and user.rol in (Rol.SUPERADMIN, Rol.MINIADMIN)


@login_required
@user_passes_test(_is_admin_or_mini)
def gestion_cuentas(request):
    estado_filtro = request.GET.get("estado", "todas")
    rol_filtro = request.GET.get("rol", "todas") # Leer el parámetro 'rol'

    usuarios = User.objects.all().order_by('first_name', 'last_name')

    if estado_filtro == "activo":
        usuarios = usuarios.filter(is_active=True)
    elif estado_filtro == "inactivo":
        usuarios = usuarios.filter(is_active=False)

    # Aplicar el filtro de rol
    if rol_filtro != "todas":
        if rol_filtro == "sin_rol":
            # Si se filtra por "Usuario Normal", incluir todos los roles correspondientes
            roles_usuario_normal = [Rol.SIN_ROL, Rol.LECTOR, Rol.EDITOR, Rol.COMENTARISTA]
            usuarios = usuarios.filter(rol__in=roles_usuario_normal)
        else:
            # Para otros roles específicos, filtrar directamente
            usuarios = usuarios.filter(rol=rol_filtro)

    return render(
        request,
        "login/accounts_manage.html",
        {
            "usuarios": usuarios,
            "estado_actual": estado_filtro,
            "rol_actual": rol_filtro
        },
    )


@login_required
@user_passes_test(_is_admin_or_mini)
@require_POST
def toggle_active(request, cedula):
    u = get_object_or_404(User, cedula=cedula)
    action = request.POST.get("action")
    u.is_active = action == "activate"
    u.save()

    estado_txt = "activada" if u.is_active else "desactivada"
    send_mail(
        f"Tu cuenta ha sido {estado_txt}",
        (
            f"Hola {u.first_name},\n\n"
            f"Tu cuenta ha sido {estado_txt}.\n"
            "Si tienes problemas, contacta a un administrador.\n\n"
            "Saludos,\n"
            "Equipo de Acreditación"
        ),
        settings.DEFAULT_FROM_EMAIL,
        [u.email],
        fail_silently=False,
    )
    return redirect(request.META.get("HTTP_REFERER", "gestion_cuentas"))

@login_required
@user_passes_test(_is_admin_or_mini) # Apply the same permission decorator
@require_POST # Ensures this view only accepts POST requests
def change_user_rol(request, cedula):
    user_to_change = get_object_or_404(User, cedula=cedula)
    new_rol_value = request.POST.get("new_rol")

    # Optional: Prevent admin from changing their own role through this interface
    # if user_to_change == request.user:
    #     messages.error(request, "No puedes cambiar tu propio rol desde esta interfaz.")
    #     return redirect(request.META.get("HTTP_REFERER", "gestion_cuentas"))

    allowed_roles = [Rol.SIN_ROL, Rol.SUPERADMIN, Rol.MINIADMIN, Rol.ACADI]

    if new_rol_value in [role.value for role in allowed_roles]:
        # Check if the new role is actually different
        if user_to_change.rol == new_rol_value:
            messages.info(request, f"{user_to_change.get_full_name} ya tiene el rol de {user_to_change.get_rol_display()}.")
        else:
            user_to_change.rol = new_rol_value
            user_to_change.save() # The save() method in User model handles is_staff/is_superuser [cite: 44, 45, 46]
            messages.success(request, f"El rol de {user_to_change.get_full_name} ha sido cambiado a {user_to_change.get_rol_display()}.")
            
            # Optionally, send an email notification about the role change
            # send_mail(...)
    else:
        messages.error(request, "Rol no válido seleccionado.")

    return redirect(request.META.get("HTTP_REFERER", "gestion_cuentas"))