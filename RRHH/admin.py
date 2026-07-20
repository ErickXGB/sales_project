from django.contrib import admin
from .models import (
    TipoSobretiempo, Empleado, Sobretiempo, SobretiempoDetalle,
    TipoPrestamo, Prestamo, PrestamoDetalle
)

admin.site.register(TipoSobretiempo)
if not admin.site.is_registered(Empleado):
    admin.site.register(Empleado)
admin.site.register(TipoPrestamo)

class SobretiempoDetalleInline(admin.TabularInline):
    model = SobretiempoDetalle
    extra = 1

@admin.register(Sobretiempo)
class SobretiempoAdmin(admin.ModelAdmin):
    inlines = [SobretiempoDetalleInline]
    list_display = ('empleado', 'fecha_registro', 'total_calculado')


class PrestamoDetalleInline(admin.TabularInline):
    model = PrestamoDetalle
    extra = 0
    fields = ('numero_cuota', 'fecha_vencimiento', 'valor_cuota', 'saldo_cuota')


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    inlines = [PrestamoDetalleInline]
    list_display = ('id', 'empleado', 'tipo_prestamo', 'fecha_prestamo', 'monto', 'monto_pagar', 'saldo', 'estado')
    list_filter = ('estado', 'tipo_prestamo', 'fecha_prestamo')
    search_fields = ('empleado__nombres', 'tipo_prestamo__descripcion')

