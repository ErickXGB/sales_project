# Módulo de Compras (purchasing)

Este módulo gestiona el registro de adquisiciones y el abastecimiento de inventario. Con el fin de mantener la consistencia en el esquema de base de datos y adherirse al principio DRY (Don't Repeat Yourself), el módulo `purchasing` reutiliza directamente las entidades core definidas en el módulo `billing` (Facturación/Inventario).

## Relación y Reutilización de Modelos

En `purchasing/models.py`, se importan y vinculan las entidades compartidas:

1. **`Supplier` (Proveedores)**:
   - El modelo `Purchase` (cabecera de compra) establece una relación de clave foránea (`ForeignKey`) con `Supplier`. Esto permite asociar cada adquisición a un proveedor único, compartiendo el mismo maestro de proveedores del sistema.

2. **`Product` (Productos)**:
   - El modelo `PurchaseDetail` (línea de detalle de compra) se relaciona mediante una clave foránea (`ForeignKey`) con `Product`. De este modo, se especifica qué productos del catálogo de inventario están siendo reabastecidos.

### Implementación técnica de las importaciones:

```python
from billing.models import Supplier, Product
```

## Beneficios de este diseño

- **Catálogo Único**: Evita la duplicidad de información al no tener tablas separadas para productos o proveedores en cada aplicación.
- **Trazabilidad**: Permite cruzar fácilmente información de compras (abastecimiento) y ventas (facturación) para calcular márgenes de ganancia y costos promedio sobre un mismo conjunto de registros.
- **Integridad Referencial**: Los mecanismos de protección de Django (por ejemplo, `on_delete=models.PROTECT`) garantizan que no se elimine un producto o proveedor que posea transacciones de compra registradas.



### ORM

10.1 CREATE
samsung = Brand.objects.create(name='Samsung', description='Electronics')
apple = Brand.objects.create(name='Apple')
electronics = ProductGroup.objects.create(name='Electronics')
dist = Supplier.objects.create(name='TechDist', email='info@tech.com')
global_s = Supplier.objects.create(name='GlobalSupply')
phone = Product.objects.create(name='Galaxy S24', brand=samsung, group=electronics, unit_price=999.99, stock=50)
phone.suppliers.add(dist, global_s)  # M2M
client = Customer.objects.create(dni='0912345678', first_name='Juan', last_name='Perez')
profile = CustomerProfile.objects.create(customer=client, taxpayer_type='ruc', payment_terms='credit_30', credit_limit=5000)
inv = Invoice.objects.create(customer=client, subtotal=999.99, tax=120, total=1119.99)
det = InvoiceDetail.objects.create(invoice=inv, product=phone, quantity=1, unit_price=phone.unit_price)

10.2 READ
Brand.objects.all()                         # Todos
Brand.objects.get(name='Samsung')            # Uno
Product.objects.filter(unit_price__gt=500)   # Precio > 500
Product.objects.filter(unit_price__range=(100,500))  # Entre
Product.objects.filter(name__icontains='gal')  # Contiene
Product.objects.exclude(stock=0)             # Excluir
Product.objects.order_by('-unit_price')      # Ordenar
Product.objects.count()                      # Contar
Product.objects.filter(stock=0).exists()     # Existe?

10.3 UPDATE
b = Brand.objects.get(name='Samsung'); b.description = 'Updated'; b.save()
Product.objects.filter(stock=0).update(is_active=False)  # Masivo
p = Product.objects.get(name='Galaxy S24')
p.suppliers.add(global_s)       # M2M: agregar
p.suppliers.remove(global_s)    # M2M: quitar
p.suppliers.clear()             # M2M: quitar todos
p.suppliers.set([dist])         # M2M: reemplazar
c = Customer.objects.get(dni='0912345678')
c.profile.credit_limit = 10000; c.profile.save()  # OneToOne
from django.db.models import F
Product.objects.update(unit_price=F('unit_price') * 1.10)  # F()

10.4 DELETE
Brand.objects.get(name='Nike').delete()
Product.objects.filter(is_active=False).delete()
product.suppliers.remove(dist)  # Solo quita relación M2M

10.5 Relaciones
# FK
product.brand.name
samsung.products.all()
# M2M
product.suppliers.all()
supplier.products.all()
Product.objects.filter(suppliers__name='TechDist')
# OneToOne
client.profile.credit_limit
profile.customer.full_name
Customer.objects.filter(profile__taxpayer_type='ruc')
# Q()
from django.db.models import Q
Product.objects.filter(Q(brand__name='Samsung') | Q(unit_price__gt=1000))

10.6 Agregaciones
from django.db.models import Sum, Avg, Max, Min, Count
Product.objects.aggregate(avg=Avg('unit_price'))
Product.objects.aggregate(max=Max('unit_price'), min=Min('unit_price'))
Invoice.objects.filter(customer__dni='0912345678').aggregate(total=Sum('total'))
Brand.objects.annotate(n=Count('products')).values('name', 'n')
Product.objects.annotate(ns=Count('suppliers')).values('name', 'ns')



python manage.py shell_plus --print-sql


Acceso al Entorno Interactivo: Se explica cómo ejecutar la consola clásica (python manage.py shell) y la recomendada consola avanzada (python manage.py shell_plus de django-extensions) que auto-importa todos los modelos al iniciar.
CREATE (10.1): Detalles sobre cómo instanciar e insertar registros directamente y cómo manejar relaciones M2M y OneToOne.
READ (10.2): Explicación de los QuerySets perezosos, métodos de filtrado con operadores avanzados (__gt, __range, __icontains) y métodos de evaluación rápida (count, exists).
UPDATE (10.3): Diferencias entre la actualización por instancia (save()) y las masivas (update()), administración de colecciones M2M y el uso seguro de F() para evitar condiciones de carrera.
DELETE (10.4): Detalle del comportamiento de borrado lógico vs. físico y cómo desacoplar relaciones M2M sin eliminar el objeto.
RELACIONES (10.5): Instrucciones sobre cómo navegar a través de claves foráneas (hacia adelante y hacia atrás), relaciones de muchos a muchos, relaciones de uno a uno y búsquedas complejas con Q().
AGREGACIONES Y ANOTACIONES (10.6): Contraste práctico entre aggregate() (devuelve un diccionario consolidado de todo el query) y annotate() (genera agrupaciones e inyecta campos calculados a nivel de fila).