from django.db import models
from django.contrib.auth.models import User
from shared.validators import validate_cedula_ec

# Create your models here.

class Brand(models.Model):
    """Marcas de productos."""
    name = models.CharField(max_length=100, unique=True, verbose_name='Brand Name')
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='brands/', blank=True, null=True, verbose_name='Imagen de Marca')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Brand'
        verbose_name_plural = 'Brands'
        ordering = ['name']
        permissions = [
            ("download_brand_pdf", "Can download Brand PDF report"),
            ("download_brand_excel", "Can download Brand Excel report"),
            ("detail_brand", "Can view Brand detail modal"),
        ]
    def __str__(self): return self.name

class ProductGroup(models.Model):
    """Grupos/categorías de productos."""
    name = models.CharField(max_length=100, unique=True, verbose_name='Group Name')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Product Group'
        verbose_name_plural = 'Product Groups'
        ordering = ['name']
        permissions = [
            ("download_productgroup_pdf", "Can download ProductGroup PDF report"),
            ("download_productgroup_excel", "Can download ProductGroup Excel report"),
            ("detail_productgroup", "Can view ProductGroup detail modal"),
        ]
    def __str__(self): return self.name

class Supplier(models.Model):
    """Proveedores. M2M con Product."""
    name = models.CharField(max_length=200, verbose_name='Company Name')
    contact_name = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'
        ordering = ['name']
        permissions = [
            ("download_supplier_pdf", "Can download Supplier PDF report"),
            ("download_supplier_excel", "Can download Supplier Excel report"),
            ("detail_supplier", "Can view Supplier detail modal"),
        ]
    def __str__(self): return self.name

class Product(models.Model):
    """Productos. FK a Brand/Group, M2M a Supplier."""
    name = models.CharField(max_length=200, verbose_name='Product Name')
    description = models.TextField(default="", verbose_name='Descripción')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products')
    group = models.ForeignKey(ProductGroup, on_delete=models.PROTECT, related_name='products')
    suppliers = models.ManyToManyField(Supplier, related_name='products', blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Imagen')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['name']
        permissions = [
            ("download_product_pdf", "Can download Product PDF report"),
            ("download_product_excel", "Can download Product Excel report"),
            ("detail_product", "Can view Product detail modal"),
        ]
    def __str__(self): return f'{self.name} ({self.brand.name})'
    @property
    def balance(self):
        return self.unit_price * self.stock

class Customer(models.Model):
    """Clientes. OneToOne con CustomerProfile."""
    dni = models.CharField(max_length=13, unique=True, verbose_name='DNI/RUC', validators=[validate_cedula_ec])
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['last_name', 'first_name']
        permissions = [
            ("download_customer_pdf", "Can download Customer PDF report"),
            ("download_customer_excel", "Can download Customer Excel report"),
            ("detail_customer", "Can view Customer detail modal"),
        ]
    def __str__(self): return f'{self.last_name}, {self.first_name}'
    @property
    def full_name(self): return f'{self.first_name} {self.last_name}'

class CustomerProfile(models.Model):
    """Perfil extendido. OneToOne con Customer."""
    TAXPAYER = [('final','Final Consumer'),('ruc','RUC'),('rise','RISE')]
    PAYMENT = [('cash','Cash'),('credit_15','15 days'),('credit_30','30 days'),('credit_60','60 days')]
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='profile')
    taxpayer_type = models.CharField(max_length=10, choices=TAXPAYER, default='final')
    payment_terms = models.CharField(max_length=15, choices=PAYMENT, default='cash')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    class Meta: verbose_name = 'Customer Profile'
    def __str__(self): return f'Profile: {self.customer}'

class Invoice(models.Model):
    """Cabecera de factura."""
    empresa = models.ForeignKey('Empresa', on_delete=models.PROTECT, related_name='invoices', null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    invoice_date = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    
    # Nuevos campos para cobros
    numero = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name='Número de Factura')
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
    metodo_pago = models.CharField(
        max_length=20,
        choices=[('EFECTIVO', 'Efectivo'), ('TRANSFERENCIA', 'Transferencia'), ('PAYPAL', 'PayPal'), ('CREDITO', 'Crédito')],
        default='EFECTIVO',
        verbose_name='Método de Pago'
    )
    
    # Campos para Facturación Electrónica SRI
    clave_acceso = models.CharField(max_length=49, unique=True, blank=True, null=True, verbose_name='Clave de Acceso SRI')
    estado_sri = models.CharField(
        max_length=20,
        choices=[('PENDIENTE', 'Pendiente'), ('AUTORIZADO', 'Autorizado'), ('RECHAZADO', 'Rechazado')],
        default='PENDIENTE',
        verbose_name='Estado SRI'
    )


    class Meta:
        ordering = ['-invoice_date']
        permissions = [
            ("download_invoice_pdf", "Can download Invoice PDF report"),
            ("download_invoice_excel", "Can download Invoice Excel report"),
            ("detail_invoice", "Can view Invoice detail page"),
            ("whatsapp_invoice", "Can send Invoice via WhatsApp"),
        ]
    def __str__(self): return f'Invoice #{self.id} - {self.customer}'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            if self.tipo_pago == 'CREDITO' or self.metodo_pago == 'PAYPAL':
                self.saldo = self.total
                self.estado = 'PENDIENTE'
            else:
                self.saldo = 0.00
                self.estado = 'PAGADA'
        super().save(*args, **kwargs)
        if not self.numero:
            self.numero = f"FAC-{self.id:06d}"
            super().save(update_fields=['numero'])

    @property
    def whatsapp_phone(self):
        """Devuelve el número de teléfono del cliente formateado para WhatsApp (solo dígitos)."""
        if not self.customer.phone:
            return ""
        # Limpiar el número conservando el signo '+' si está presente al inicio
        cleaned = "".join(c for c in self.customer.phone if c.isdigit() or c == '+')
        if cleaned.startswith('+'):
            return cleaned[1:]
        
        # Respaldo de prefijo por defecto si no se ingresó con prefijo (ej. Ecuador: 593)
        digits_only = "".join(c for c in cleaned if c.isdigit())
        if len(digits_only) == 10 and digits_only.startswith('0'):
            digits_only = '593' + digits_only[1:]
        elif len(digits_only) == 9 and digits_only.startswith('9'):
            digits_only = '593' + digits_only
        return digits_only

    @property
    def whatsapp_message(self):
        """Genera el mensaje pre-redactado para enviar al cliente por WhatsApp."""
        msg = (
            f"Estimado/a *{self.customer.full_name}*,\n\n"
            f"Le informamos que se ha registrado una transacción sobre su *Factura #{self.numero or f'FAC-{self.id:06d}'}* emitida el {self.invoice_date.strftime('%d/%m/%Y')}.\n\n"
            f"*Detalles del Documento:*\n"
            f"- Subtotal: ${self.subtotal}\n"
            f"- IVA (15%): ${self.tax}\n"
            f"- Total: ${self.total}\n"
            f"- Saldo Pendiente: ${self.saldo}\n"
            f"- Estado de Pago: {self.get_estado_display()}\n\n"
            f"Agradecemos su preferencia.\n"
            f"Saludos cordiales."
        )
        return msg


class InvoiceDetail(models.Model):
    """Líneas de factura."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='invoice_details')
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    def __str__(self): return f'{self.product.name} x {self.quantity}'
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class Empresa(models.Model):
    usuarios = models.ManyToManyField(User, related_name='empresas', blank=True)
    ruc = models.CharField("RUC", max_length=13, unique=True, validators=[validate_cedula_ec])
    razon_social = models.CharField("Razón Social", max_length=300)
    nombre_comercial = models.CharField("Nombre Comercial", max_length=300)
    dir_matriz = models.CharField("Dirección Matriz", max_length=300)
    dir_establecimiento = models.CharField("Dirección Establecimiento", max_length=300)
    obligado_contabilidad = models.BooleanField("Obligado a llevar Contabilidad", default=False)
    
    # Serie de facturación
    codigo_establecimiento = models.CharField("Código Establecimiento", max_length=3, default="001")
    codigo_punto_emision = models.CharField("Punto de Emisión", max_length=3, default="001")
    secuencial_factura = models.IntegerField("Siguiente Secuencial de Factura", default=1)

    ambiente = models.CharField("Ambiente SRI", max_length=1, choices=[('1', 'Pruebas'), ('2', 'Producción')], default='1')
    is_active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['razon_social']

    def __str__(self):
        return f"{self.razon_social} ({self.ruc})"





