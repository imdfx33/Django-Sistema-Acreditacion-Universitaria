from django.http import HttpResponseForbidden

def role_required(*roles):
    """
    Decorador que permite el acceso solo a usuarios con un rol específico.
    Puedes pasar varios roles como argumentos: @role_required('admin_completo' ,'admin_light', 'director')
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if hasattr(request.user, 'rol_id') and request.user.rol_id.name in roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("No tienes permiso para acceder a esta página.")
        return _wrapped_view
    return decorator
