from django.contrib import admin
from .models import CobroFactura

@admin.register(CobroFactura)
class CobroFacturaAdmin(admin.ModelAdmin):
    list_display = ['id', 'factura', 'fecha', 'valor', 'observacion']
    list_filter = ['fecha', 'factura__estado']
    search_fields = ['factura__numero', 'factura__customer__first_name', 'factura__customer__last_name', 'observacion']
