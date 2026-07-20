from django.db import models, transaction
from django.core.exceptions import ValidationError
from billing.models import Invoice
from purchasing.models import Purchase

class CobroFactura(models.Model):
    factura = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name='cobros',
        verbose_name='Factura'
    )
    fecha = models.DateTimeField(verbose_name='Fecha/Hora de Cobro')
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor Pagado'
    )
    observacion = models.TextField(
        blank=True,
        verbose_name='Observación'
    )

    class Meta:
        verbose_name = 'Cobro de Factura'
        verbose_name_plural = 'Cobros de Facturas'
        ordering = ['-fecha', '-id']
        permissions = [
            ("download_cobrofactura_pdf", "Can download CobroFactura PDF report"),
            ("download_cobrofactura_excel", "Can download CobroFactura Excel report"),
            ("detail_cobrofactura", "Can view CobroFactura details"),
            ("whatsapp_cobrofactura", "Can send CobroFactura via WhatsApp"),
        ]

    def __str__(self):
        return f"Abono #{self.id} - {self.factura.numero or f'FAC-{self.factura.id:06d}'} - ${self.valor}"

    def clean(self):
        super().clean()
        
        try:
            factura = self.factura
        except (Invoice.DoesNotExist, AttributeError):
            return

        # Validación de fecha: no permitir fechas anteriores a la actual
        if self.fecha is not None:
            from django.utils import timezone
            local_fecha = timezone.localtime(self.fecha) if timezone.is_aware(self.fecha) else self.fecha
            if local_fecha.date() < timezone.localdate():
                raise ValidationError({'fecha': "La fecha del abono no puede ser anterior a la fecha actual."})

        # Validaciones de negocio básicas
        if self.valor is not None:
            if self.valor <= 0:
                raise ValidationError({'valor': "El valor del abono debe ser mayor que cero."})

            # No permitir pagar una factura anulada/desactivada
            if not factura.is_active or factura.estado == 'ANULADA':
                raise ValidationError("No se puede registrar un pago sobre una factura anulada o inactiva.")

            # Calcular saldo potencial
            if self.pk:
                original = CobroFactura.objects.get(pk=self.pk)
                diff = self.valor - original.valor
                potential_saldo = factura.saldo - diff
            else:
                potential_saldo = factura.saldo - self.valor

            # No permitir pagar más que el saldo
            if potential_saldo < 0:
                # Si es edición, el saldo disponible anterior era factura.saldo + original.valor
                available_balance = factura.saldo
                if self.pk:
                    available_balance += original.valor
                raise ValidationError({'valor': f"El valor del abono no puede superar el saldo pendiente de la factura (${available_balance})."})

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            factura = Invoice.objects.select_for_update().get(pk=self.factura.pk)
            
            if self.pk:
                original = CobroFactura.objects.select_for_update().get(pk=self.pk)
                diff = self.valor - original.valor
                factura.saldo -= diff
            else:
                factura.saldo -= self.valor

            # Ajustar estado según el saldo
            if factura.saldo == 0:
                factura.estado = 'PAGADA'
            else:
                factura.estado = 'PENDIENTE'

            factura.save()
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            factura = Invoice.objects.select_for_update().get(pk=self.factura.pk)
            
            # Validación: Eliminar pago (solo si la factura no está pagada completamente)
            if factura.estado == 'PAGADA':
                raise ValidationError("No se puede eliminar un pago de una factura que está totalmente pagada.")

            # Validación: No permitir eliminar un pago cuando deje inconsistente el saldo (ej. saldo + valor > total)
            new_saldo = factura.saldo + self.valor
            if new_saldo > factura.total:
                raise ValidationError("Inconsistencia de saldo: Al revertir este pago, el saldo de la factura superaría el total de la misma.")

            factura.saldo = new_saldo
            factura.estado = 'PENDIENTE'
            factura.save()
            super().delete(*args, **kwargs)


class PagoCompra(models.Model):
    compra = models.ForeignKey(
        Purchase,
        on_delete=models.PROTECT,
        related_name='pagos',
        verbose_name='Compra'
    )
    fecha = models.DateField(verbose_name='Fecha de Pago')
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor Pagado'
    )
    observacion = models.TextField(
        blank=True,
        verbose_name='Observación'
    )

    class Meta:
        verbose_name = 'Pago de Compra'
        verbose_name_plural = 'Pagos de Compras'
        ordering = ['-fecha', '-id']
        permissions = [
            ("download_pagocompra_pdf", "Can download PagoCompra PDF report"),
            ("download_pagocompra_excel", "Can download PagoCompra Excel report"),
            ("detail_pagocompra", "Can view PagoCompra details"),
            ("whatsapp_pagocompra", "Can send PagoCompra via WhatsApp"),
        ]

    def __str__(self):
        return f"Pago #{self.id} - Compra {self.compra.document_number} - ${self.valor}"

    def clean(self):
        super().clean()
        
        try:
            compra = self.compra
        except (Purchase.DoesNotExist, AttributeError):
            return

        # Validación de fecha: no permitir fechas anteriores a la actual
        if self.fecha is not None:
            from django.utils import timezone
            if self.fecha < timezone.localdate():
                raise ValidationError({'fecha': "La fecha del pago no puede ser anterior a la fecha actual."})

        # Validaciones de negocio
        if self.valor is not None:
            if self.valor <= 0:
                raise ValidationError({'valor': "El valor del pago debe ser mayor que cero."})

            if not compra.is_active or compra.estado == 'ANULADA':
                raise ValidationError("No se puede registrar un pago sobre una compra inactiva o anulada.")

            # Calcular saldo potencial
            if self.pk:
                original = PagoCompra.objects.get(pk=self.pk)
                diff = self.valor - original.valor
                potential_saldo = compra.saldo - diff
            else:
                potential_saldo = compra.saldo - self.valor

            if potential_saldo < 0:
                available_balance = compra.saldo
                if self.pk:
                    available_balance += original.valor
                raise ValidationError({'valor': f"El valor del pago no puede superar el saldo pendiente de la compra (${available_balance})."})

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            compra = Purchase.objects.select_for_update().get(pk=self.compra.pk)
            
            if self.pk:
                original = PagoCompra.objects.select_for_update().get(pk=self.pk)
                diff = self.valor - original.valor
                compra.saldo -= diff
            else:
                compra.saldo -= self.valor

            # Ajustar estado según el saldo
            if compra.saldo == 0:
                compra.estado = 'PAGADA'
            else:
                compra.estado = 'PENDIENTE'

            compra.save()
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            compra = Purchase.objects.select_for_update().get(pk=self.compra.pk)
            
            if compra.estado == 'PAGADA':
                raise ValidationError("No se puede eliminar un pago de una compra que ya está completamente pagada.")

            new_saldo = compra.saldo + self.valor
            if new_saldo > compra.total:
                raise ValidationError("Inconsistencia de saldo: Al revertir este pago, el saldo de la compra superaría el total de la misma.")

            compra.saldo = new_saldo
            compra.estado = 'PENDIENTE'
            compra.save()
            super().delete(*args, **kwargs)
