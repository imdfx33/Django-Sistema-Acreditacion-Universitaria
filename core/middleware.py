# core/middleware.py

import re
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, resolve

class LoginRequiredMiddleware:
    """
    Middleware que obliga a iniciar sesión en todas las vistas,
    salvo las rutas exentas (login, logout y las definidas en LOGIN_EXEMPT_URLS).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Patrón para la ruta de login (p.ej.: 'login/')
        login_url = settings.LOGIN_URL.lstrip('/')
        self.exempt_urls = [re.compile(f'^{re.escape(login_url)}/?$')]
        # Rutas adicionales exentas (p.ej.: registro, restablecer contraseña, etc.)
        for expr in getattr(settings, 'LOGIN_EXEMPT_URLS', []):
            self.exempt_urls.append(re.compile(expr))
    
    def __call__(self, request):
        # Intentamos obtener el nombre de la URL resuelta
        try:
            url_name = resolve(request.path_info).url_name
        except:
            url_name = None

        # 1) Si el usuario YA está autenticado y pide el 'login', 
        #    redirígelo inmediatamente al home (/home/)
        if request.user.is_authenticated and url_name == 'login':
            return redirect(settings.LOGIN_REDIRECT_URL)

        # 2) Si el usuario YA está autenticado y pide 'logout',
        #    simplemente sigue (para que efectúe el logout)
        if request.user.is_authenticated and url_name == 'logout':
            return self.get_response(request)

        # 3) Si NO está autenticado, sólo permitimos las URLs exentas...
        if not request.user.is_authenticated:
            path = request.path_info.lstrip('/')
            for pattern in self.exempt_urls:
                if pattern.match(path):
                    return self.get_response(request)
            # ...y si no es ruta exenta, vamos directo al login “puro”
            return redirect(settings.LOGIN_URL)

        # 4) En cualquier otro caso (usuario autenticado y vista normal), seguir
        return self.get_response(request)