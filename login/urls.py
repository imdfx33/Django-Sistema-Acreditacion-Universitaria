# login/urls.py
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views
from django.contrib.auth.views import LogoutView
from .views import login_view
from django.contrib.auth.views import LogoutView as BaseLogoutView
from login.views import avatar_proxy

class LogoutView(BaseLogoutView):
    http_method_names = ['get', 'post', 'head', 'options', 'trace']

urlpatterns = [
    path('avatar/<str:file_id>/', views.avatar_proxy, name='avatar_proxy'),
    path('perfil/', views.profile_view, name='profile'),
    path('perfil/avatar/', views.upload_avatar, name='upload_avatar'),
    path('perfil/avatar/delete/', views.delete_avatar, name='delete_avatar'),

    path('', login_view, name='login'),

    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    path('register/', views.register_start,  name='register_start'),
    path('verify/',   views.register_verify, name='register_verify'),
    path('usuarios/', views.usuarios_panel,  name='usuarios_panel'), # no funcional
    
    path('perfil/', views.profile_view,          name='profile'),
    path('perfil/editar/', views.update_profile, name='edit_profile'),
    path('perfil/avatar/', views.upload_avatar,  name='upload_avatar'),
    path('perfil/avatar/delete/', views.delete_avatar, name='delete_avatar'),


    # –––––– Olvidó contraseña/usuario ––––––
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='login/password_reset.html',
        email_template_name='login/password_reset_email.html',
        subject_template_name='login/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='login/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='login/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),

    path('password_reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='login/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    path('accounts/gestion/', views.gestion_cuentas, name='gestion_cuentas'),
    # Toggle estado de usuario (POST)
    path('accounts/gestion/toggle/<str:cedula>/', views.toggle_active, name='toggle_active'),

    path('accounts/gestion/change_rol/<str:cedula>/', views.change_user_rol, name='change_user_rol'),
]
