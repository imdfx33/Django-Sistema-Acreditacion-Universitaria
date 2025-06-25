# login/backends.py
from django.contrib.auth.backends import ModelBackend
from .models import User

class CedulaBackend(ModelBackend):
    """
    Autenticación por cédula (USERNAME_FIELD='cedula').
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Django envía el valor de <input name="username">
        cedula = username or kwargs.get('cedula')
        if not cedula:
            return None
        try:
            user = User.objects.get(pk=cedula)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
