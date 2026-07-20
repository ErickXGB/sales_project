from django.db import models
from decimal import Decimal
from billing.models import Supplier, Product   # Reutilizamos modelos de billing
 
 
class Purchase(models.Model):
    """Cabecera de compra. Documenta una adquisición a un proveedor."""
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name='purchases'
    )
    document_number = models.CharField(
        max_length=20, verbose_name='Supplier Invoice No.'
    )
    purchase_date = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
 
    # Nuevos campos para pagos de compras
    tipo_pago = models.CharField(
        max_length=10,
        choices=[('CONTADO', 'Contado'), ('CREDITO', 'Crédito')],
        default='CREDITO',
        verbose_name='Tipo de Pago'
    )
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name='Saldo')
    estado = models.CharField(
        max_length=15,
        choices=[('PENDIENTE', 'Pendiente'), ('PAGADA', 'Pagada'), ('ANULADA', 'Anulada')],
        default='PENDIENTE',
        verbose_name='Estado'
    )

    class Meta:
        verbose_name = 'Purchase'
        verbose_name_plural = 'Purchases'
        ordering = ['-purchase_date']
        constraints = [
            models.UniqueConstraint(fields=['supplier', 'document_number'], name='unique_supplier_document')
        ]
        permissions = [
            ("download_purchase_pdf", "Can download Purchase PDF report"),
            ("download_purchase_excel", "Can download Purchase Excel report"),
            ("detail_purchase", "Can view Purchase detail page"),
            ("whatsapp_purchase", "Can send Purchase via WhatsApp"),
        ]
 
    def __str__(self):
        return f'Purchase #{self.id} - {self.supplier}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            if self.tipo_pago == 'CREDITO':
                self.saldo = self.total
                self.estado = 'PENDIENTE'
            else:
                self.saldo = 0.00
                self.estado = 'PAGADA'
        super().save(*args, **kwargs)

    @property
    def whatsapp_phone(self):
        """Devuelve el número de teléfono del proveedor formateado para WhatsApp (solo dígitos)."""
        if not self.supplier.phone:
            return ""
        cleaned = "".join(c for c in self.supplier.phone if c.isdigit())
        if len(cleaned) == 10 and cleaned.startswith('0'):
            cleaned = '593' + cleaned[1:]
        elif len(cleaned) == 9 and cleaned.startswith('9'):
            cleaned = '593' + cleaned
        return cleaned

    @property
    def whatsapp_message(self):
        """Genera el mensaje pre-redactado para enviar al proveedor por WhatsApp."""
        msg = (
            f"Hola *{self.supplier.name}*,\n\n"
            f"Le informamos que hemos registrado un abono/pago sobre la *Compra #{self.document_number}* por nuestra adquisición del {self.purchase_date.strftime('%d/%m/%Y')}.\n\n"
            f"*Detalles de la Transacción:*\n"
            f"- Subtotal: ${self.subtotal}\n"
            f"- IVA (15%): ${self.tax}\n"
            f"- Total de Compra: ${self.total}\n"
            f"- Saldo Restante: ${self.saldo}\n"
            f"- Estado de Pago: {self.get_estado_display()}\n\n"
            f"Saludos cordiales."
        )
        return msg
 
 
class PurchaseDetail(models.Model):
    """Líneas de compra. Cada fila es un producto adquirido."""
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name='details'
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='purchase_details'
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
 
    def __str__(self):
        return f'{self.product.name} x {self.quantity}'
 
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
