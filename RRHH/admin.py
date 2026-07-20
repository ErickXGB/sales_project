from django.contrib import admin
from .models import TipoSobretiempo, Empleado, Sobretiempo, SobretiempoDetalle

admin.site.register(TipoSobretiempo)
admin.site.register(Empleado)

# Registrar Maestro-Detalle inline en el admin para facilidad de auditoría
class SobretiempoDetalleInline(admin.TabularInline):
    model = SobretiempoDetalle
    extra = 1

@admin.register(Sobretiempo)
class SobretiempoAdmin(admin.ModelAdmin):
    inlines = [SobretiempoDetalleInline]
    list_display = ('empleado', 'fecha_registro', 'total_calculado')
