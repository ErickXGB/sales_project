import json
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Avg, Q
from decimal import Decimal
from billing.models import Supplier, Product
from .models import Purchase, PurchaseDetail

@login_required
def purchase_list(request):
    """Lista todas las compras con búsqueda por campo (igual que product_list)."""
    purchases = Purchase.objects.select_related('supplier').all()

    search_field = request.GET.get('search_field', 'all').strip()
    search_value = request.GET.get('search_value', '').strip()

    if search_value:
        if search_field == 'supplier' or search_field == 'all':
            if search_field == 'all':
                purchases = purchases.filter(
                    Q(supplier__name__icontains=search_value) |
                    Q(document_number__icontains=search_value) |
                    Q(purchase_date__icontains=search_value) |
                    Q(total__icontains=search_value)
                )
            else:
                purchases = purchases.filter(supplier__name__icontains=search_value)
        elif search_field == 'document':
            purchases = purchases.filter(document_number__icontains=search_value)
        elif search_field == 'date':
            purchases = purchases.filter(purchase_date__date__icontains=search_value)
        elif search_field == 'total':
            purchases = purchases.filter(total__icontains=search_value)
        elif search_field == 'active':
            is_active = search_value.lower() in ['activo', 'si', 'sí', '1', 'true', 'yes']
            purchases = purchases.filter(is_active=is_active)

    context = {
        'items': purchases,
        'search_field': search_field,
        'search_value': search_value,
    }
    return render(request, 'purchasing/purchase_list.html', context)

@login_required
def purchase_create(request):
    """Crea una compra con sus detalles usando entrada dinámica (JS)."""
    if request.method == 'POST':
        supplier_select = request.POST.get('supplier_select', '').strip()
        supplier_name = request.POST.get('supplier_name', '').strip()
        supplier_contact_name = request.POST.get('supplier_contact_name', '').strip()
        supplier_email = request.POST.get('supplier_email', '').strip() or None
        supplier_phone = request.POST.get('supplier_phone', '').strip() or None
        supplier_address = request.POST.get('supplier_address', '').strip() or None
        document_number = request.POST.get('document_number', '').strip()
        
        product_ids = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        unit_costs = request.POST.getlist('unit_cost[]')
        
        errors = []
        if not supplier_select:
            errors.append("Debe seleccionar un proveedor o elegir '-- Nuevo Proveedor --'.")
            
        if not document_number:
            errors.append("El número de documento es obligatorio.")
            
        if supplier_select == 'new':
            if not supplier_name:
                errors.append("El nombre del proveedor es obligatorio para un nuevo proveedor.")
            if supplier_phone:
                phone_cleaned = re.sub(r'\s+|-', '', supplier_phone)
                if not re.match(r'^\d+$', phone_cleaned):
                    errors.append("El teléfono del proveedor solo debe contener números.")
        
        if not product_ids:
            errors.append("Debe agregar al menos un producto a la compra.")
            
        if len(product_ids) != len(quantities) or len(product_ids) != len(unit_costs):
            errors.append("Datos de productos incorrectos.")
            
        # Comprobar duplicado antes de guardar
        if supplier_select and supplier_select != 'new':
            if Purchase.objects.filter(supplier_id=supplier_select, document_number=document_number).exists():
                errors.append(f"El número de documento '{document_number}' ya está registrado para este proveedor.")
        elif supplier_select == 'new' and supplier_name:
            if Purchase.objects.filter(supplier__name=supplier_name, document_number=document_number).exists():
                errors.append(f"El número de documento '{document_number}' ya está registrado para el proveedor '{supplier_name}'.")

        items_to_save = []
        # Uso de decimal para evitar errores de redondeo
        subtotal = Decimal('0.00')
        
        for idx in range(len(product_ids)):
            p_id = product_ids[idx]
            qty_str = quantities[idx]
            cost_str = unit_costs[idx]
            
            if not p_id or not qty_str or not cost_str:
                errors.append(f"Fila {idx+1}: Complete todos los campos del producto.")
                continue
                
            try:
                qty = int(qty_str)
                cost = Decimal(cost_str)
            except (ValueError, TypeError):
                errors.append(f"Fila {idx+1}: Cantidad o costo no válidos.")
                continue
                
            if qty <= 0:
                errors.append(f"Fila {idx+1}: La cantidad debe ser mayor que cero.")
                continue
                
            if cost < 0:
                errors.append(f"Fila {idx+1}: El costo no puede ser negativo.")
                continue
                
            product = Product.objects.filter(id=p_id).first()
            if not product:
                errors.append(f"Fila {idx+1}: El producto seleccionado no existe.")
                continue
                
            line_subtotal = qty * cost
            subtotal += line_subtotal
            items_to_save.append({
                'product': product,
                'quantity': qty,
                'unit_cost': cost,
                'subtotal': line_subtotal
            })
            
        if errors:
            for err in errors:
                messages.error(request, err)
            return _render_form_with_errors(request, supplier_select, supplier_name, supplier_contact_name, supplier_email, supplier_phone, supplier_address, document_number, product_ids, quantities, unit_costs)
            
        try:
            with transaction.atomic():
                if supplier_select and supplier_select != 'new':
                    supplier = Supplier.objects.get(id=supplier_select)
                    supplier.name = supplier_name
                    supplier.contact_name = supplier_contact_name
                    supplier.email = supplier_email
                    supplier.phone = supplier_phone
                    supplier.address = supplier_address
                    supplier.save()
                else:
                    supplier = Supplier.objects.create(
                        name=supplier_name,
                        contact_name=supplier_contact_name,
                        email=supplier_email,
                        phone=supplier_phone,
                        address=supplier_address
                    )
                
                # Verificar de nuevo que no exista
                if Purchase.objects.filter(supplier=supplier, document_number=document_number).exists():
                    raise Exception(f"El número de documento '{document_number}' ya está registrado para este proveedor.")
                
                tax = subtotal * Decimal('0.15')
                total = subtotal + tax
                
                purchase = Purchase.objects.create(
                    supplier=supplier,
                    document_number=document_number,
                    subtotal=subtotal,
                    tax=tax,
                    total=total,
                    is_active=True
                )
                
                for item in items_to_save:
                    PurchaseDetail.objects.create(
                        purchase=purchase,
                        product=item['product'],
                        quantity=item['quantity'],
                        unit_cost=item['unit_cost'],
                        subtotal=item['subtotal']
                    )
                    # ACTUALIZAR STOCK: suma la cantidad comprada al stock del producto
                    Product.objects.filter(id=item['product'].id).update(stock=F('stock') + item['quantity'])
                    
            messages.success(request, f"Compra #{purchase.id} guardada con éxito. Stock actualizado.")
            return redirect('purchasing:purchase_list')
            
        except Exception as e:
            messages.error(request, f"Error al guardar la compra: {str(e)}")
            return _render_form_with_errors(request, supplier_select, supplier_name, supplier_contact_name, supplier_email, supplier_phone, supplier_address, document_number, product_ids, quantities, unit_costs)
            
    else:
        return _render_form(request)

def _render_form(request, context_opts=None):
    if context_opts is None:
        context_opts = {}
    suppliers = Supplier.objects.filter(is_active=True)
    products = Product.objects.filter(is_active=True).select_related('brand')
    
    suppliers_json = []
    for s in suppliers:
        suppliers_json.append({
            'id': s.id,
            'name': s.name,
            'contact_name': s.contact_name or '',
            'email': s.email or '',
            'phone': s.phone or '',
            'address': s.address or '',
        })
        
    products_json = []
    for p in products:
        products_json.append({
            'id': p.id,
            'name': f"{p.name} ({p.brand.name})",
            'price': float(p.unit_price),
        })
        
    context = {
        'title': 'Crear Compra',
        'suppliers': suppliers,
        'products': products,
        'suppliers_json_str': json.dumps(suppliers_json),
        'products_json_str': json.dumps(products_json),
    }
    context.update(context_opts)
    return render(request, 'purchasing/purchase_form.html', context)

def _render_form_with_errors(request, supplier_select, supplier_name, supplier_contact_name, supplier_email, supplier_phone, supplier_address, document_number, product_ids, quantities, unit_costs):
    posted_values = {
        'supplier_select': supplier_select,
        'supplier_name': supplier_name,
        'supplier_contact_name': supplier_contact_name,
        'supplier_email': supplier_email or '',
        'supplier_phone': supplier_phone or '',
        'supplier_address': supplier_address or '',
        'document_number': document_number,
    }
    
    selected_items = []
    for idx in range(len(product_ids)):
        try:
            selected_items.append({
                'product_id': int(product_ids[idx]) if product_ids[idx] else '',
                'quantity': int(quantities[idx]) if quantities[idx] else 1,
                'unit_cost': float(unit_costs[idx]) if unit_costs[idx] else 0.00
            })
        except Exception:
            selected_items.append({
                'product_id': product_ids[idx],
                'quantity': quantities[idx],
                'unit_cost': unit_costs[idx]
            })
            
    return _render_form(request, {
        'posted_values_json': json.dumps(posted_values),
        'selected_items_json': json.dumps(selected_items),
    })

@login_required
def purchase_detail(request, pk):
    """Detalle de una compra con prefetch_related('details__product')."""
    purchase = get_object_or_404(
        Purchase.objects.select_related('supplier').prefetch_related('details__product'),
        pk=pk
    )
    return render(request, 'purchasing/purchase_detail.html', {'purchase': purchase})

@login_required
def purchase_delete(request, pk):
    """Elimina una compra y todos sus detalles (CASCADE)."""
    purchase = get_object_or_404(Purchase, pk=pk)
    if request.method == 'POST':
        purchase_id = purchase.id
        purchase.delete()
        messages.success(request, f'¡Compra #{purchase_id} eliminada con éxito!')
        return redirect('purchasing:purchase_list')
    return render(request, 'purchasing/purchase_confirm_delete.html', {'object': purchase})

@login_required
def purchase_report(request):
    """Reporte de costo promedio por producto."""
    products = Product.objects.annotate(
        avg_cost=Avg('purchase_details__unit_cost')
    ).select_related('brand', 'group').order_by('name')
    
    overall_avg = PurchaseDetail.objects.aggregate(avg_cost=Avg('unit_cost'))['avg_cost'] or Decimal('0.00')
    
    context = {
        'products': products,
        'overall_avg': overall_avg,
    }
    return render(request, 'purchasing/purchase_report.html', context)


