from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

# Diccionario: rol -> lista de codenames de permisos
ROLES = {
    # El Administrador recibe TODOS los permisos de facturación y compras
    'Administrador': '__all__',

    # El Gerente puede consultar todo y generar reportes, pero no borrar/modificar/crear
    'Gerente': [
        'view_brand', 'view_productgroup', 'view_supplier', 'view_product',
        'view_customer', 'view_customerprofile', 'view_invoice', 'view_invoicedetail',
        'view_purchase', 'view_purchasedetail',
    ],

    # Compras administra Proveedores, Compras y Detalles de compra. Puede ver catálogo de productos.
    'Compras': [
        'view_brand', 'view_productgroup', 'view_product',
        'view_supplier', 'add_supplier', 'change_supplier', 'delete_supplier',
        'view_purchase', 'add_purchase', 'change_purchase', 'delete_purchase',
        'view_purchasedetail', 'add_purchasedetail', 'change_purchasedetail', 'delete_purchasedetail',
    ],

    # Ventas administra Clientes, Facturas (Ventas) y Detalles de venta. Puede ver catálogo de productos.
    'Ventas': [
        'view_product',
        'view_customer', 'add_customer', 'change_customer', 'delete_customer',
        'view_customerprofile', 'add_customerprofile', 'change_customerprofile', 'delete_customerprofile',
        'view_invoice', 'add_invoice', 'change_invoice', 'delete_invoice',
        'view_invoicedetail', 'add_invoicedetail', 'change_invoicedetail', 'delete_invoicedetail',
    ],
}

class Command(BaseCommand):
    help = 'Crea los roles del sistema (Administrador, Gerente, Compras, Ventas) con sus permisos correspondientes'

    def handle(self, *args, **kwargs):
        # Limpieza opcional de roles antiguos que ya no se usan
        roles_to_remove = ['Vendedor', 'Analista de Compras']
        for r_name in roles_to_remove:
            Group.objects.filter(name=r_name).delete()
            self.stdout.write(self.style.WARNING(f'Rol antiguo "{r_name}" eliminado (si existía)'))

        for role_name, codenames in ROLES.items():
            group, created = Group.objects.get_or_create(name=role_name)

            if codenames == '__all__':
                perms = Permission.objects.filter(content_type__app_label__in=['billing', 'purchasing'])
            else:
                perms = Permission.objects.filter(codename__in=codenames)

            group.permissions.set(perms)

            status = 'creado' if created else 'actualizado'
            self.stdout.write(self.style.SUCCESS(
                f'Rol "{role_name}" {status} con {perms.count()} permisos'
            ))

