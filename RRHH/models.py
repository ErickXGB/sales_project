from django.db import models
from decimal import Decimal

class TipoSobretiempo(models.Model):
    codigo = models.CharField(max_length=10)
    descripcion = models.CharField(max_length=100)
    factor = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return self.descripcion


class Empleado(models.Model):
    nombres = models.CharField(max_length=100)
    sueldo = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nombres


class Sobretiempo(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    fecha_registro = models.DateField()
    total_horas = models.PositiveIntegerField(default=240)
    sueldo_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    total_calculado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        default=0
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['empleado', 'fecha_registro'], name='unique_sobretiempo_empleado_fecha')
        ]

    def __str__(self):
        return f"Sobretiempo de {self.empleado} - {self.fecha_registro}"

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if hasattr(self, 'empleado') and self.empleado and self.fecha_registro:
            query = Sobretiempo.objects.filter(empleado=self.empleado, fecha_registro=self.fecha_registro)
            if self.pk:
                query = query.exclude(pk=self.pk)
            if query.exists():
                raise ValidationError({
                    'fecha_registro': f"Ya existe un registro de sobretiempo para el empleado {self.empleado} en la fecha {self.fecha_registro.strftime('%d/%m/%Y')}."
                })

    def calcular_total_maestro(self):
        """Suma el valor de todos los detalles y actualiza total_calculado."""
        total = sum(detalle.valor_calculado for detalle in self.detalles.all())
        self.total_calculado = total
        # Guardamos para evitar bucles
        super().save(update_fields=['total_calculado'])



class SobretiempoDetalle(models.Model):
    sobretiempo = models.ForeignKey(
        Sobretiempo,
        related_name="detalles",
        on_delete=models.CASCADE
    )
    tipo_sobretiempo = models.ForeignKey(
        TipoSobretiempo,
        on_delete=models.CASCADE
    )
    numero_horas = models.DecimalField(max_digits=6, decimal_places=2)
    valor_calculado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False
    )

    def save(self, *args, **kwargs):
        # fórmula: (Sueldo / 240) * Horas * Factor
        sueldo = self.sobretiempo.sueldo_mensual
        horas = self.numero_horas
        factor = self.tipo_sobretiempo.factor
        
        # Guardamos el resultado
        self.valor_calculado = (sueldo / Decimal('240')) * horas * factor
        
        super().save(*args, **kwargs)
        
        # Recalcular el total
        self.sobretiempo.calcular_total_maestro()

    def delete(self, *args, **kwargs):
        sobretiempo = self.sobretiempo
        super().delete(*args, **kwargs)
        # Recalcular el total después de eliminar la línea
        sobretiempo.calcular_total_maestro()
