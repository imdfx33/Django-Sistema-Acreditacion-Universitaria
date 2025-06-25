# login/models.py
import re
from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.conf import settings # Para AUTH_USER_MODEL

CEDULA_REGEX = r'^\d{5,15}$'              # 5-15 dígitos

class Rol(models.TextChoices):
    SUPERADMIN      = 'superadmin',      'Super Admin'
    MINIADMIN       = 'miniadmin',       'Mini Admin'
    ACADI           = 'acadi',           'ACADI' # Rol de la universidad/institución con permisos elevados
    EDITOR          = 'editor',          'Editor' # Rol genérico para usuarios finales sobre factores/proyectos
    COMENTARISTA    = 'comentarista',    'Comentarista' # Rol genérico
    LECTOR          = 'lector',          'Lector' # Rol genérico
    SIN_ROL         = 'sin_rol',         'Sin Rol'

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, cedula, email, password, **extra):
        if not cedula:
            raise ValueError('La cédula es obligatoria')
        if not re.match(CEDULA_REGEX, cedula):
            raise ValueError('Cédula inválida (5-15 dígitos)')
        if not email:
            raise ValueError('El email es obligatorio')
        if not email.endswith('@gmail.com'): # Asegurar que el email sea Gmail si es un requisito para Drive
            raise ValueError('El correo debe ser @gmail.com')
        email = self.normalize_email(email)

        user = self.model(cedula=cedula, email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, cedula, email, password=None, **extra):
        extra.setdefault('rol', Rol.SIN_ROL)
        extra.setdefault('is_active', False) # Nuevos usuarios inactivos hasta aprobación
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create_user(cedula, email, password, **extra)

    def create_superuser(self, cedula, email, password=None, **extra):
        # Los SuperAdmins de Django (is_superuser=True) también serán SuperAdmin en nuestra lógica de roles.
        extra.update({
            'rol': Rol.SUPERADMIN,
            'is_staff': True,
            'is_superuser': True,
            'is_active': True
        })
        if extra.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(cedula, email, password, **extra)

class User(AbstractBaseUser, PermissionsMixin):
    cedula      = models.CharField(primary_key=True, max_length=15)
    email       = models.EmailField(unique=True)
    first_name  = models.CharField(max_length=30)
    last_name   = models.CharField(max_length=60)
    rol         = models.CharField(max_length=15, choices=Rol.choices, default=Rol.SIN_ROL)

    is_active   = models.BooleanField(default=False) # Por defecto inactivo, requiere aprobación
    is_staff    = models.BooleanField(default=False) # Acceso al admin de Django
    date_joined = models.DateTimeField(auto_now_add=True)

    avatar      = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Foto de perfil')
    avatar_drive_id   = models.CharField(max_length=100, blank=True, null=True)
    avatar_drive_link = models.URLField(blank=True, null=True)
    
    objects = UserManager()

    USERNAME_FIELD  = 'cedula'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.cedula})'
    
    @property
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_super_admin_role(self):
        """Verifica si el usuario tiene el ROL de SuperAdmin."""
        return self.rol == Rol.SUPERADMIN

    @property
    def is_mini_admin_role(self):
        """Verifica si el usuario tiene el ROL de MiniAdmin."""
        return self.rol == Rol.MINIADMIN
        
    @property
    def is_akadi_role(self):
        """Verifica si el usuario tiene el ROL de Akadi."""
        return self.rol == Rol.ACADI

    @property
    def has_elevated_permissions(self):
        """SuperAdmin y Akadi tienen permisos totales."""
        return self.rol in (Rol.SUPERADMIN, Rol.ACADI) or self.is_superuser

    def save(self, *args, **kwargs):
        # Ensure is_staff and is_superuser are handled correctly based on role
        if self.rol == Rol.SUPERADMIN:
            self.is_staff = True
            self.is_superuser = True # [cite: 44]
        elif self.rol in (Rol.MINIADMIN, Rol.ACADI):
            self.is_staff = True # [cite: 45]
            self.is_superuser = False # [cite: 45]
        else: # SIN_ROL, EDITOR, COMENTARISTA, LECTOR
            self.is_staff = False
            self.is_superuser = False # [cite: 46]
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
