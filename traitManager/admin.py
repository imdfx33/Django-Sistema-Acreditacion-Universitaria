# traitManager/admin.py
from django.contrib import admin
from .models import Trait


@admin.register(Trait)
class TraitAdmin(admin.ModelAdmin):
    list_display = ("name", "approved_count", "total_aspects")
    search_fields = ("name",)

    def total_aspects(self, obj):
        return obj.aspects.count()
    total_aspects.short_description = "Aspectos"

    def approved_count(self, obj):
        return obj.aspects.filter(approved=True).count()
    approved_count.short_description = "Aspectos aprobados"
