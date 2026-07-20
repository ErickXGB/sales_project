from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

# Diccionario: rol -> lista de codenames de permisos
ROLES = {
    # El Administrador recibe TODOS los permisos de facturación, compras y pagos
    'Administrador': '__all__',

    # El Gerente puede consultar todo y generar reportes, pero no borrar/modificar/crear
    'Gerente': [
        'view_brand', 'detail_brand', 'download_brand_pdf', 'download_brand_excel',
        'view_productgroup', 'detail_productgroup', 'download_productgroup_pdf', 'download_productgroup_excel',
        'view_supplier', 'detail_supplier', 'download_supplier_pdf', 'download_supplier_excel',
        'view_product', 'detail_product', 'download_product_pdf', 'download_product_excel',
        'view_customer', 'detail_customer', 'download_customer_pdf', 'download_customer_excel',
        'view_customerprofile',
        'view_invoice', 'detail_invoice', 'download_invoice_pdf', 'download_invoice_excel', 'whatsapp_invoice',
        'view_invoicedetail',
        'view_purchase', 'detail_purchase', 'download_purchase_pdf', 'download_purchase_excel', 'whatsapp_purchase',
        'view_purchasedetail',
        'view_cobrofactura', 'detail_cobrofactura', 'download_cobrofactura_pdf', 'download_cobrofactura_excel', 'whatsapp_cobrofactura',
        'view_pagocompra', 'detail_pagocompra', 'download_pagocompra_pdf', 'download_pagocompra_excel', 'whatsapp_pagocompra',
        'download_user_pdf', 'download_user_excel', 'detail_user',
        # Permisos RRHH (Sobretiempos)
        'view_sobretiempo', 'view_tiposobretiempo', 'view_empleado', 'view_sobretiempodetalle',
        'detail_sobretiempo', 'download_sobretiempo_pdf', 'download_sobretiempo_excel',
    ],

    # Compras administra Proveedores, Compras, Detalles de compra y Pagos de Compras.
    'Compras': [
        'view_brand', 'detail_brand', 'view_productgroup', 'detail_productgroup', 'view_product', 'detail_product',
        'view_supplier', 'detail_supplier', 'add_supplier', 'change_supplier', 'delete_supplier',
        'view_purchase', 'detail_purchase', 'add_purchase', 'change_purchase', 'delete_purchase', 'whatsapp_purchase',
        'view_purchasedetail', 'add_purchasedetail', 'change_purchasedetail', 'delete_purchasedetail',
        'view_pagocompra', 'detail_pagocompra', 'add_pagocompra', 'change_pagocompra', 'delete_pagocompra', 'whatsapp_pagocompra',
    ],

    # Ventas administra Clientes, Facturas (Ventas), Detalles de venta y Cobros.
    'Ventas': [
        'view_product', 'detail_product',
        'view_customer', 'detail_customer', 'add_customer', 'change_customer', 'delete_customer',
        'view_customerprofile', 'add_customerprofile', 'change_customerprofile', 'delete_customerprofile',
        'view_invoice', 'detail_invoice', 'add_invoice', 'change_invoice', 'delete_invoice', 'whatsapp_invoice',
        'view_invoicedetail', 'add_invoicedetail', 'change_invoicedetail', 'delete_invoicedetail',
        'view_cobrofactura', 'detail_cobrofactura', 'add_cobrofactura', 'change_cobrofactura', 'delete_cobrofactura', 'whatsapp_cobrofactura',
    ],
}

class Command(BaseCommand):
    help = 'Crea los roles del sistema (Administrador, Gerente, Compras, Ventas) con sus permisos correspondientes'

    def handle(self, *args, **kwargs):
        # Asegurar que existan los permisos de descarga para el modelo User
        from django.contrib.contenttypes.models import ContentType
        from django.contrib.auth.models import User
        user_ct = ContentType.objects.get_for_model(User)
        Permission.objects.get_or_create(
            codename='download_user_pdf',
            content_type=user_ct,
            defaults={'name': 'Can download User PDF report'}
        )
        Permission.objects.get_or_create(
            codename='download_user_excel',
            content_type=user_ct,
            defaults={'name': 'Can download User Excel report'}
        )
        Permission.objects.get_or_create(
            codename='detail_user',
            content_type=user_ct,
            defaults={'name': 'Can view User details'}
        )

        # Asegurar que existan los permisos de descarga y detalle para Sobretiempo
        from RRHH.models import Sobretiempo
        sobretiempo_ct = ContentType.objects.get_for_model(Sobretiempo)
        Permission.objects.get_or_create(
            codename='download_sobretiempo_pdf',
            content_type=sobretiempo_ct,
            defaults={'name': 'Can download Sobretiempo PDF report'}
        )
        Permission.objects.get_or_create(
            codename='download_sobretiempo_excel',
            content_type=sobretiempo_ct,
            defaults={'name': 'Can download Sobretiempo Excel report'}
        )
        Permission.objects.get_or_create(
            codename='detail_sobretiempo',
            content_type=sobretiempo_ct,
            defaults={'name': 'Can view Sobretiempo details'}
        )

        # Limpieza opcional de roles antiguos que ya no se usan
        roles_to_remove = ['Vendedor', 'Analista de Compras']
        for r_name in roles_to_remove:
            Group.objects.filter(name=r_name).delete()
            self.stdout.write(self.style.WARNING(f'Rol antiguo "{r_name}" eliminado (si existía)'))

        for role_name, codenames in ROLES.items():
            group, created = Group.objects.get_or_create(name=role_name)

            if codenames == '__all__':
                perms = Permission.objects.filter(content_type__app_label__in=['billing', 'purchasing', 'pagos', 'RRHH'])
            else:
                perms = Permission.objects.filter(codename__in=codenames)

            group.permissions.set(perms)

            status = 'creado' if created else 'actualizado'
            self.stdout.write(self.style.SUCCESS(
                f'Rol "{role_name}" {status} con {perms.count()} permisos'
            ))

