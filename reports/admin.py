# reports/admin.py
from django.contrib import admin
from .models import FinalReport

@admin.register(FinalReport)
class FinalReportAdmin(admin.ModelAdmin):
    list_display = ('generated_at', 'generated_by_display', 'pdf_url_link')
    list_filter = ('generated_at', 'generated_by')
    search_fields = ('generated_by__email', 'generated_by__first_name', 'generated_by__last_name', 'pdf_url')
    readonly_fields = ('generated_at', 'generated_by', 'pdf_url') # Hacerlos readonly si se llenan programáticamente
    date_hierarchy = 'generated_at'

    def generated_by_display(self, obj):
        return obj.generated_by.get_full_name() if obj.generated_by else "Sistema"
    generated_by_display.short_description = "Generado por"

    def pdf_url_link(self, obj):
        from django.utils.html import format_html
        if obj.pdf_url:
            return format_html("<a href='{url}' target='_blank'>Ver PDF</a>", url=obj.pdf_url)
        return "N/A"
    pdf_url_link.short_description = "Enlace PDF"
    pdf_url_link.allow_tags = True # Necesario para versiones antiguas de Django si se usa format_html

