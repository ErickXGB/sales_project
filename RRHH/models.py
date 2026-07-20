from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

class TipoSobretiempo(models.Model):
    codigo = models.CharField(max_length=10)
    descripcion = models.CharField(max_length=100)
    factor = models.DecimalField(max_digits=4, decimal_places=2)

    def __str__(self):
        return self.descripcion


class TipoPrestamo(models.Model):
    descripcion = models.CharField(max_length=100)
    tasa_interes = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.descripcion} ({self.tasa_interes}%)"

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if self.tasa_interes is not None:
            if self.tasa_interes < 0:
                raise ValidationError({'tasa_interes': "La tasa de interés no puede ser negativa."})
            if self.tasa_interes > 50:
                raise ValidationError({'tasa_interes': "La tasa de interés máxima permitida es del 50%."})


class Empleado(models.Model):
    nombres = models.CharField(max_length=100)
    sueldo = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nombres} (${self.sueldo})"


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


class Prestamo(models.Model):
    empleado = models.ForeignKey(Empleado, on_delete=models.CASCADE)
    tipo_prestamo = models.ForeignKey(TipoPrestamo, on_delete=models.CASCADE)

    fecha_prestamo = models.DateField()

    monto = models.DecimalField(max_digits=10, decimal_places=2)
    interes = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    monto_pagar = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    numero_cuotas = models.PositiveIntegerField(default=1)

    saldo = models.DecimalField(max_digits=10, decimal_places=2, editable=False)

    ESTADOS = [
        ('PEND', 'Pendiente'),
        ('PAG', 'Pagado'),
        ('ANU', 'Anulado'),
    ]

    estado = models.CharField(max_length=4, choices=ESTADOS, default='PEND')

    def __str__(self):
        return f"Préstamo #{self.id} - {self.empleado.nombres} (${self.monto})"

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        super().clean()
        errors = {}

        if self.fecha_prestamo and not self.pk:
            if self.fecha_prestamo < timezone.localdate():
                errors['fecha_prestamo'] = f"La fecha del préstamo no puede ser anterior a la fecha actual ({timezone.localdate().strftime('%d/%m/%Y')})."

        if self.monto is not None and self.monto <= Decimal('0.00'):
            errors['monto'] = "El monto del préstamo debe ser mayor a cero."


        if self.numero_cuotas is not None and self.numero_cuotas < 1:
            errors['numero_cuotas'] = "El número de cuotas debe ser al menos 1."

        if hasattr(self, 'empleado') and self.empleado and hasattr(self, 'tipo_prestamo') and self.tipo_prestamo:
            tipo_desc = self.tipo_prestamo.descripcion.lower()
            sueldo = self.empleado.sueldo

            # Validaciones específicas según el tipo de préstamo
            if 'quirografario' in tipo_desc:
                max_monto = sueldo * Decimal('12')
                max_cuotas = 36
                if self.monto and self.monto > max_monto:
                    errors['monto'] = f"Para un préstamo Quirografario, el monto máximo es de 12 sueldos (${max_monto:.2f})."
                if self.numero_cuotas and self.numero_cuotas > max_cuotas:
                    errors['numero_cuotas'] = f"El número máximo de cuotas para un préstamo Quirografario es de {max_cuotas} meses."

            elif 'hipotecario' in tipo_desc:
                max_monto = sueldo * Decimal('50')
                max_cuotas = 60
                if self.monto and self.monto > max_monto:
                    errors['monto'] = f"Para un préstamo Hipotecario, el monto máximo es de 50 sueldos (${max_monto:.2f})."
                if self.numero_cuotas and self.numero_cuotas > max_cuotas:
                    errors['numero_cuotas'] = f"El número máximo de cuotas para un préstamo Hipotecario es de {max_cuotas} meses."

            elif 'emergente' in tipo_desc or 'salud' in tipo_desc:
                max_monto = sueldo * Decimal('3')
                max_cuotas = 12
                if self.monto and self.monto > max_monto:
                    errors['monto'] = f"Para un préstamo Emergente/Salud, el monto máximo es de 3 sueldos (${max_monto:.2f})."
                if self.numero_cuotas and self.numero_cuotas > max_cuotas:
                    errors['numero_cuotas'] = f"El número máximo de cuotas para un préstamo Emergente es de {max_cuotas} meses."

            # Validación de capacidad de endeudamiento: la cuota no debe superar el 50% del sueldo del empleado
            if self.monto and self.numero_cuotas and self.tipo_prestamo and 'monto' not in errors and 'numero_cuotas' not in errors:
                tasa = Decimal(str(self.tipo_prestamo.tasa_interes))
                interes_est = (Decimal(str(self.monto)) * tasa / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                monto_total_est = self.monto + interes_est
                valor_cuota_est = monto_total_est / Decimal(self.numero_cuotas)
                max_cuota_permitida = sueldo * Decimal('0.50')
                if valor_cuota_est > max_cuota_permitida:
                    errors['numero_cuotas'] = (
                        f"La cuota calculada (${valor_cuota_est:.2f}) excede el 50% del sueldo del empleado "
                        f"(${max_cuota_permitida:.2f}). Aumente el número de cuotas o reduzca el monto."
                    )

        if errors:
            raise ValidationError(errors)


    def calcular_totales(self):
        """Calcula el interés y el monto total a pagar."""
        if self.monto and self.tipo_prestamo:
            tasa = Decimal(str(self.tipo_prestamo.tasa_interes))
            self.interes = (Decimal(str(self.monto)) * tasa / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            self.monto_pagar = Decimal(str(self.monto)) + self.interes
        else:
            self.interes = Decimal('0.00')
            self.monto_pagar = Decimal('0.00')

    def generar_o_actualizar_detalles(self):
        """Genera automáticamente el detalle de cuotas de acuerdo al número de cuotas ingresado."""
        if not self.pk or self.numero_cuotas < 1 or not self.monto_pagar:
            return

        # Si aún no se han creado cuotas para este préstamo, las generamos automáticamente
        if not self.detalles.exists():
            num_cuotas = self.numero_cuotas
            monto_total = self.monto_pagar
            cuota_base = (monto_total / Decimal(num_cuotas)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Ajuste de redondeo en la última cuota
            suma_cuotas_base = cuota_base * (num_cuotas - 1) if num_cuotas > 1 else Decimal('0.00')
            ultima_cuota = monto_total - suma_cuotas_base

            fecha_base = self.fecha_prestamo
            for i in range(1, num_cuotas + 1):
                fecha_venc = fecha_base + timedelta(days=30 * i)
                val_cuota = ultima_cuota if i == num_cuotas else cuota_base
                PrestamoDetalle.objects.create(
                    prestamo=self,
                    numero_cuota=i,
                    fecha_vencimiento=fecha_venc,
                    valor_cuota=val_cuota,
                    saldo_cuota=val_cuota
                )

        self.actualizar_saldo_y_estado()

    def actualizar_saldo_y_estado(self):
        """Actualiza el saldo pendiente y gestiona el estado del préstamo."""
        if not self.pk:
            return
        
        detalles = list(self.detalles.all())
        if detalles:
            saldo_calculado = sum(d.saldo_cuota for d in detalles)
        else:
            saldo_calculado = self.monto_pagar or Decimal('0.00')
            
        self.saldo = saldo_calculado
        
        if self.estado != 'ANU':
            if self.saldo <= Decimal('0.00') and self.monto_pagar > Decimal('0.00'):
                self.estado = 'PAG'
            elif self.estado == 'PAG' and self.saldo > Decimal('0.00'):
                self.estado = 'PEND'
        else:
            self.saldo = Decimal('0.00')
            
        super().save(update_fields=['saldo', 'estado'])

    def save(self, *args, **kwargs):
        self.calcular_totales()
        if self.saldo is None and self.monto_pagar:
            self.saldo = self.monto_pagar
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.generar_o_actualizar_detalles()


class PrestamoDetalle(models.Model):
    prestamo = models.ForeignKey(
        Prestamo,
        related_name="detalles",
        on_delete=models.CASCADE
    )

    numero_cuota = models.PositiveIntegerField()

    fecha_vencimiento = models.DateField()

    valor_cuota = models.DecimalField(max_digits=10, decimal_places=2)

    saldo_cuota = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['numero_cuota']

    def __str__(self):
        return f"Cuota #{self.numero_cuota} de Préstamo #{self.prestamo.id} (${self.valor_cuota})"

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        errors = {}

        if self.numero_cuota is not None and self.numero_cuota < 1:
            errors['numero_cuota'] = "El número de cuota debe ser mayor o igual a 1."

        if self.valor_cuota is not None and self.valor_cuota <= Decimal('0.00'):
            errors['valor_cuota'] = "El valor de la cuota debe ser mayor a cero."

        if self.saldo_cuota is not None:
            if self.saldo_cuota < Decimal('0.00'):
                errors['saldo_cuota'] = "El saldo de la cuota no puede ser negativo."
            if self.valor_cuota is not None and self.saldo_cuota > self.valor_cuota:
                errors['saldo_cuota'] = "El saldo de la cuota no puede exceder el valor original de la cuota."

        if hasattr(self, 'prestamo') and self.prestamo and self.fecha_vencimiento:
            if self.prestamo.fecha_prestamo and self.fecha_vencimiento < self.prestamo.fecha_prestamo:
                errors['fecha_vencimiento'] = f"La fecha de vencimiento no puede ser anterior a la fecha del préstamo ({self.prestamo.fecha_prestamo.strftime('%d/%m/%Y')})."

            if self.numero_cuota and self.numero_cuota > self.prestamo.numero_cuotas:
                errors['numero_cuota'] = f"El número de cuota ({self.numero_cuota}) no puede ser mayor que el total de cuotas del préstamo ({self.prestamo.numero_cuotas})."

            # Validar pago secuencial: no se puede pagar cuota N si cuota N-1 está pendiente
            if self.pk and self.saldo_cuota is not None and self.valor_cuota is not None and self.saldo_cuota < self.valor_cuota:
                cuota_ant = PrestamoDetalle.objects.filter(
                    prestamo=self.prestamo,
                    numero_cuota__lt=self.numero_cuota,
                    saldo_cuota__gt=Decimal('0.00')
                ).exclude(pk=self.pk).order_by('numero_cuota').first()
                if cuota_ant:
                    errors['saldo_cuota'] = f"No puede registrar pago en la cuota #{self.numero_cuota} sin haber saldado primero la cuota #{cuota_ant.numero_cuota}."

        if errors:
            raise ValidationError(errors)


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.prestamo.actualizar_saldo_y_estado()

    def delete(self, *args, **kwargs):
        prestamo = self.prestamo
        super().delete(*args, **kwargs)
        prestamo.actualizar_saldo_y_estado()


