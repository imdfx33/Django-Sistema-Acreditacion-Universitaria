# login/admin.py
from django.contrib import admin
from .models import User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display  = ('cedula', 'first_name', 'last_name', 'email', 'rol', 'is_active')
    list_filter   = ('rol', 'is_active')
    search_fields = ('cedula', 'first_name', 'last_name', 'email')
