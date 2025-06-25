# login/forms.py
import re, random, string
from django import forms
from django.core.mail import send_mail
from django.contrib.auth import authenticate, password_validation
from .models import User, Rol, CEDULA_REGEX

PWD_REGEX = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$'

# ---------- Paso 1 – registro ----------
class RegisterStep1Form(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput,
                                label='Contraseña')
    password2 = forms.CharField(widget=forms.PasswordInput,
                                label='Confirmar contraseña')

    class Meta:
        model  = User
        fields = ('cedula', 'first_name', 'last_name', 'email')

    # ---- validaciones ----
    def clean_cedula(self):
        cd = self.cleaned_data['cedula']
        if not re.match(CEDULA_REGEX, cd):
            raise forms.ValidationError('Cédula inválida')
        return cd

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if not email.endswith('@gmail.com'):
            raise forms.ValidationError('El correo debe ser @gmail.com')
        return email

    def clean_password1(self):
        pwd = self.cleaned_data['password1']
        if not re.match(PWD_REGEX, pwd):
            raise forms.ValidationError(
                'Min. 8 caracteres con mayúscula, minúscula, número y símbolo')
        return pwd

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password1') != cleaned.get('password2'):
            self.add_error('password2', 'No coincide')
        return cleaned

    # ---- helper para enviar código ----
    def enviar_codigo(self, request):
        email  = self.cleaned_data['email']
        codigo = ''.join(random.choices(string.digits, k=6))

        # guardamos datos en sesión
        request.session['pending_user'] = {
            'cedula':     self.cleaned_data['cedula'],
            'first_name': self.cleaned_data['first_name'],
            'last_name':  self.cleaned_data['last_name'],
            'email':      email,
            'password':   self.cleaned_data['password1'],
        }
        request.session['codigo_' + email] = codigo

        send_mail(
            'Código de verificación – Proyecto Acreditación',
            f'Tu código es: {codigo}',
            None,
            [email],
            fail_silently=False
        )

# ---------- Paso 2 – verificación ----------
class VerifyCodeForm(forms.Form):
    codigo = forms.CharField(max_length=6,
                            label='Código de verificación')

    def __init__(self, *args, **kwargs):
        self.email   = kwargs.pop('email')
        self.session = kwargs.pop('session')
        super().__init__(*args, **kwargs)

    def clean_codigo(self):
        codigo = self.cleaned_data['codigo']
        if not codigo.isdigit() or len(codigo) != 6:
            raise forms.ValidationError('El código debe tener 6 dígitos')
        return codigo

    def clean(self):
        cleaned      = super().clean()
        session_code = self.session.get('codigo_' + self.email)
        if session_code != cleaned.get('codigo'):
            self.add_error('codigo', 'Código incorrecto')
        return cleaned

# ---------- Login ----------
class LoginForm(forms.Form):
    cedula   = forms.CharField(label='Cédula')
    password = forms.CharField(widget=forms.PasswordInput,
                                label='Contraseña')

    def clean(self):
        cleaned = super().clean()
        cedula  = cleaned.get('cedula')
        pwd     = cleaned.get('password')
        if cedula and pwd:
            user = authenticate(username=cedula, password=pwd)
            if not user:
                raise forms.ValidationError('Credenciales incorrectas')
            if not user.is_active:
                raise forms.ValidationError('Cuenta inactiva – espera aprobación')
            cleaned['user'] = user
        return cleaned

# ---------- Perfil ----------
class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label='Nombre',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Tu nombre'})
    )
    last_name = forms.CharField(
        label='Apellido',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Tu apellido'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name']

    def clean_first_name(self):
        nombre = self.cleaned_data['first_name'].strip().upper()
        if not nombre:
            raise forms.ValidationError('El nombre no puede estar vacío.')
        return nombre

    def clean_last_name(self):
        apellido = self.cleaned_data['last_name'].strip().upper()
        if not apellido:
            raise forms.ValidationError('El apellido no puede estar vacío.')
        return apellido

# ---------- Foto de perfil ----------
class AvatarUploadForm(forms.ModelForm):
    avatar = forms.ImageField(label='Foto de perfil', required=True)

    class Meta:
        model = User
        fields = ['avatar']

    def clean_avatar(self):
        img = self.cleaned_data.get('avatar')
        if img:
            # Validar tipo
            valid_mime = ['image/jpeg', 'image/png']
            if img.content_type not in valid_mime:
                raise forms.ValidationError('Formato no válido. Solo se permiten JPG o PNG.')
            # Validar tamaño (< 2 MB)
            max_size = 2 * 1024 * 1024
            if img.size > max_size:
                raise forms.ValidationError('El tamaño máximo permitido es 2 MB.')
        return img
