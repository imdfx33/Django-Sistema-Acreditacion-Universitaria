# aspectManager/admin.py
from django.contrib import admin
from .models import Aspect


@admin.register(Aspect)
class AspectAdmin(admin.ModelAdmin):
    list_display = ("name", "weight", "approved")
    list_filter = ("approved",)
    search_fields = ("name",)
