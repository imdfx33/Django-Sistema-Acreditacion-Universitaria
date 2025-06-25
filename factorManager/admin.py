from django.contrib import admin
from .models import Factor, Project


@admin.register(Factor)
class FactorAdmin(admin.ModelAdmin):
    list_display  = ('name', 'start_date', 'end_date',
                    'approved_percentage', 'status')
    list_filter   = ('status',)
    search_fields = ('name',)
