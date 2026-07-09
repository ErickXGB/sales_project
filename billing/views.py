import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.views import View
from django.db import transaction
from decimal import Decimal
import json
from .models import *
from .forms import SignUpForm, BrandForm, ProductGroupForm, SupplierForm, ProductForm, CustomerForm, InvoiceForm, InvoiceDetailFormSet
from shared.mixins import StaffRequiredMixin, PermissionRequiredMixin
from django.utils.decorators import method_decorator
from shared.decorators import audit_action, permission_required

# === REGISTRO ===
class SignUpView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('billing:brand_list')

    def test_func(self):
        # Desactivado para el público general; solo superusuarios (o admin) pueden acceder.
        return self.request.user.is_superuser

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

@login_required
def home(request):
    """Vista principal del sistema. Muestra resumen general."""
    context = {
        'total_brands': Brand.objects.count(),
        'total_products': Product.objects.count(),
        'total_customers': Customer.objects.count(),
        'total_invoices': Invoice.objects.count(),
        'recent_invoices': Invoice.objects.all()[:5],  # Últimas 5
        'low_stock': Product.objects.filter(stock__lte=5, is_active=True),
    }
    return render(request, 'billing/home.html', context)


# === BRAND (FBV) ===
@login_required
@permission_required('billing.view_brand')
@audit_action('LIST_BRANDS')  
def brand_list(request):
    search_field = request.GET.get('search_field', 'all').strip()
    search_value = request.GET.get('search_value', '').strip()
    
    brands = Brand.objects.all()
    
    if search_value:
        from django.db.models import Q
        if search_field == 'name':
            brands = brands.filter(name__icontains=search_value)
        elif search_field == 'description':
            brands = brands.filter(description__icontains=search_value)
        elif search_field == 'active':
            val = search_value.lower()
            if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                brands = brands.filter(is_active=True)
            elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                brands = brands.filter(is_active=False)
        else: # 'all'
            q_filters = Q(name__icontains=search_value) | Q(description__icontains=search_value)
            val = search_value.lower()
            if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                q_filters |= Q(is_active=True)
            elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                q_filters |= Q(is_active=False)
            brands = brands.filter(q_filters)
            
    return render(request, 'billing/brand_list.html', {
        'brands': brands,
        'search_field': search_field,
        'search_value': search_value
    })

@login_required
@permission_required('billing.add_brand')
@audit_action('CREATE_BRAND')  
def brand_create(request):
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Marca creada con éxito!')
            return redirect('billing:brand_list')
    else: form = BrandForm()
    return render(request, 'billing/brand_form.html', {'form':form, 'title':'Crear Marca'})

@login_required
@permission_required('billing.change_brand')
@audit_action('UPDATE_BRAND')  
def brand_update(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Marca actualizada con éxito!')
            return redirect('billing:brand_list')
    else: form = BrandForm(instance=brand)
    return render(request, 'billing/brand_form.html', {'form':form, 'title':'Editar Marca'})

@login_required
@permission_required('billing.delete_brand')
@audit_action('DELETE_BRAND')  
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        brand.delete()
        messages.success(request, '¡Marca eliminada con éxito!')
        return redirect('billing:brand_list')
    return render(request, 'billing/brand_confirm_delete.html', {'object': brand})

# =============================================
# CRUD DE INVOICE - VISTAS BASADAS EN FUNCIONES
# (Requiere FBV porque usa formsets complejos)
# =============================================

@login_required
@permission_required('billing.view_invoice')
def invoice_list(request):
    """Lista todas las facturas con sus totales."""
    invoices = Invoice.objects.select_related('customer').all()
    return render(request, 'billing/invoice_list.html', {'items': invoices})


@login_required
@permission_required('billing.add_invoice')
def invoice_create(request):
    """Crea factura con sus líneas de detalle."""
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        formset = InvoiceDetailFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # Guardar factura (sin commit para asignar totales)
            invoice = form.save(commit=False)
            invoice.save()

            # Asignar la factura al formset y guardar detalles
            formset.instance = invoice
            details = formset.save()

            # Calcular totales
            subtotal = sum(d.subtotal for d in invoice.details.all())
            invoice.subtotal = subtotal
            invoice.tax = subtotal * Decimal('0.15')  # IVA 15%
            invoice.total = invoice.subtotal + invoice.tax
            invoice.save()

            messages.success(request, f'¡Factura #{invoice.id} creada con éxito! Total: ${invoice.total}')
            return redirect('billing:invoice_list')
    else:
        form = InvoiceForm()
        formset = InvoiceDetailFormSet()

    return render(request, 'billing/invoice_form.html', {
        'form': form,
        'formset': formset,
        'title': 'Crear Factura',
    })


@login_required
@permission_required('billing.view_invoice')
def invoice_detail(request, pk):
    """Muestra el detalle completo de una factura."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('customer')
                       .prefetch_related('details__product'),
        pk=pk
    )
    return render(request, 'billing/invoice_detail.html', {'invoice': invoice})


@login_required
@permission_required('billing.delete_invoice')
def invoice_delete(request, pk):
    """Elimina una factura y todos sus detalles (CASCADE)."""
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        invoice_id = invoice.id
        invoice.delete()
        messages.success(request, f'¡Factura #{invoice_id} eliminada con éxito!')
        return redirect('billing:invoice_list')
    return render(request, 'billing/invoice_confirm_delete.html', {'object': invoice})


# === PRODUCTGROUP (CBV) ===
class ProductGroupListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'billing.view_productgroup'
    model = ProductGroup
    template_name = 'billing/productgroup_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        queryset = super().get_queryset()
        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()
        if search_value:
            from django.db.models import Q
            if search_field == 'name':
                queryset = queryset.filter(name__icontains=search_value)
            elif search_field == 'active':
                val = search_value.lower()
                if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                    queryset = queryset.filter(is_active=True)
                elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                    queryset = queryset.filter(is_active=False)
            else: # 'all'
                q_filters = Q(name__icontains=search_value)
                val = search_value.lower()
                if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                    q_filters |= Q(is_active=True)
                elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                    q_filters |= Q(is_active=False)
                queryset = queryset.filter(q_filters)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context

class ProductGroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'billing.add_productgroup'
    model = ProductGroup; form_class = ProductGroupForm; template_name = 'billing/productgroup_form.html'; success_url = reverse_lazy('billing:productgroup_list')
class ProductGroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'billing.change_productgroup'
    model = ProductGroup; form_class = ProductGroupForm; template_name = 'billing/productgroup_form.html'; success_url = reverse_lazy('billing:productgroup_list')
class ProductGroupDeleteView(LoginRequiredMixin, PermissionRequiredMixin, StaffRequiredMixin, DeleteView):
    permission_required = 'billing.delete_productgroup'
    model = ProductGroup
    template_name = 'billing/productgroup_confirm_delete.html'
    success_url = reverse_lazy('billing:productgroup_list')
    staff_redirect_url = '/groups/'  # Redirige aquí si no es staff


# === SUPPLIER (CBV) ===
class SupplierListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'billing.view_supplier'
    model = Supplier
    template_name = 'billing/supplier_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        queryset = super().get_queryset()
        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()
        if search_value:
            from django.db.models import Q
            if search_field == 'name':
                queryset = queryset.filter(name__icontains=search_value)
            elif search_field == 'contact_name':
                queryset = queryset.filter(contact_name__icontains=search_value)
            elif search_field == 'email':
                queryset = queryset.filter(email__icontains=search_value)
            elif search_field == 'phone':
                queryset = queryset.filter(phone__icontains=search_value)
            elif search_field == 'active':
                val = search_value.lower()
                if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                    queryset = queryset.filter(is_active=True)
                elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                    queryset = queryset.filter(is_active=False)
            else: # 'all'
                q_filters = Q(name__icontains=search_value) | \
                            Q(contact_name__icontains=search_value) | \
                            Q(email__icontains=search_value) | \
                            Q(phone__icontains=search_value)
                val = search_value.lower()
                if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                    q_filters |= Q(is_active=True)
                elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                    q_filters |= Q(is_active=False)
                queryset = queryset.filter(q_filters)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context

class SupplierCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'billing.add_supplier'
    model = Supplier; form_class = SupplierForm; template_name = 'billing/supplier_form.html'; success_url = reverse_lazy('billing:supplier_list')
class SupplierUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'billing.change_supplier'
    model = Supplier; form_class = SupplierForm; template_name = 'billing/supplier_form.html'; success_url = reverse_lazy('billing:supplier_list')
class SupplierDeleteView(LoginRequiredMixin, PermissionRequiredMixin, StaffRequiredMixin, DeleteView):
    permission_required = 'billing.delete_supplier'
    model = Supplier
    template_name = 'billing/supplier_confirm_delete.html'
    success_url = reverse_lazy('billing:supplier_list')
    staff_redirect_url = '/suppliers/'

# === PRODUCT (CBV) ===
class ProductListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'billing.view_product'
    model = Product
    template_name = 'billing/product_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('brand', 'group').prefetch_related('suppliers')
        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()

        if search_value:
            from django.db.models import Q
            if search_field == 'name':
                queryset = queryset.filter(name__icontains=search_value)
            elif search_field == 'brand':
                queryset = queryset.filter(brand__name__icontains=search_value)
            elif search_field == 'group':
                queryset = queryset.filter(group__name__icontains=search_value)
            elif search_field == 'supplier':
                queryset = queryset.filter(suppliers__name__icontains=search_value).distinct()
            elif search_field == 'price':
                try:
                    price_val = Decimal(search_value)
                    queryset = queryset.filter(unit_price=price_val)
                except Exception:
                    queryset = queryset.none()
            elif search_field == 'stock':
                if search_value.isdigit():
                    queryset = queryset.filter(stock=int(search_value))
                else:
                    queryset = queryset.none()
            elif search_field == 'active':
                val = search_value.lower()
                if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                    queryset = queryset.filter(is_active=True)
                elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                    queryset = queryset.filter(is_active=False)
            else: # 'all'
                q_filters = Q(name__icontains=search_value) | \
                            Q(brand__name__icontains=search_value) | \
                            Q(group__name__icontains=search_value) | \
                            Q(suppliers__name__icontains=search_value)
                
                if search_value.isdigit():
                    q_filters |= Q(stock=int(search_value))
                try:
                    price_val = Decimal(search_value)
                    q_filters |= Q(unit_price=price_val)
                except Exception:
                    pass
                
                val = search_value.lower()
                if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                    q_filters |= Q(is_active=True)
                elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                    q_filters |= Q(is_active=False)
                
                queryset = queryset.filter(q_filters).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context

class ProductCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'billing.add_product'
    model = Product; form_class = ProductForm; template_name = 'billing/product_form.html'; success_url = reverse_lazy('billing:product_list')
class ProductUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'billing.change_product'
    model = Product; form_class = ProductForm; template_name = 'billing/product_form.html'; success_url = reverse_lazy('billing:product_list')
class ProductDeleteView(LoginRequiredMixin, PermissionRequiredMixin, StaffRequiredMixin, DeleteView):
    permission_required = 'billing.delete_product'
    model = Product
    template_name = 'billing/product_confirm_delete.html'
    success_url = reverse_lazy('billing:product_list')
    staff_redirect_url = '/products/'

# === CUSTOMER (CBV) ===
class CustomerListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'billing.view_customer'
    model = Customer
    template_name = 'billing/customer_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        queryset = super().get_queryset()
        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()

        if search_value:
            from django.db.models import Q
            if search_field == 'name':
                queryset = queryset.filter(Q(first_name__icontains=search_value) | Q(last_name__icontains=search_value))
            elif search_field == 'dni':
                queryset = queryset.filter(dni__icontains=search_value)
            elif search_field == 'email':
                queryset = queryset.filter(email__icontains=search_value)
            elif search_field == 'phone':
                queryset = queryset.filter(phone__icontains=search_value)
            elif search_field == 'active':
                val = search_value.lower()
                if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                    queryset = queryset.filter(is_active=True)
                elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                    queryset = queryset.filter(is_active=False)
            else: # 'all'
                q_filters = Q(first_name__icontains=search_value) | \
                            Q(last_name__icontains=search_value) | \
                            Q(dni__icontains=search_value) | \
                            Q(email__icontains=search_value) | \
                            Q(phone__icontains=search_value)
                val = search_value.lower()
                if val in ['activo', 'activa', 'si', 'sí', '1', 'true']:
                    q_filters |= Q(is_active=True)
                elif val in ['inactivo', 'inactiva', 'no', '0', 'false']:
                    q_filters |= Q(is_active=False)
                queryset = queryset.filter(q_filters)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context

class CustomerCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'billing.add_customer'
    model = Customer; form_class = CustomerForm; template_name = 'billing/customer_form.html'; success_url = reverse_lazy('billing:customer_list')
class CustomerUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'billing.change_customer'
    model = Customer; form_class = CustomerForm; template_name = 'billing/customer_form.html'; success_url = reverse_lazy('billing:customer_list')
class CustomerDeleteView(LoginRequiredMixin, PermissionRequiredMixin, StaffRequiredMixin, DeleteView):
    permission_required = 'billing.delete_customer'
    model = Customer
    template_name = 'billing/customer_confirm_delete.html'
    success_url = reverse_lazy('billing:customer_list')
    staff_redirect_url = '/customers/'

# === INVOICE (CBV) ===
class InvoiceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'billing.view_invoice'
    model = Invoice
    template_name = 'billing/invoice_list.html'
    context_object_name = 'items'

    def get_queryset(self):
        queryset = super().get_queryset()
        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()

        if search_value:
            from django.db.models import Q
            if search_field == 'id':
                if search_value.isdigit():
                    queryset = queryset.filter(id=int(search_value))
                else:
                    queryset = queryset.none()
            elif search_field == 'customer_name':
                queryset = queryset.filter(
                    Q(customer__first_name__icontains=search_value) |
                    Q(customer__last_name__icontains=search_value)
                )
            elif search_field == 'customer_dni':
                queryset = queryset.filter(customer__dni__icontains=search_value)
            elif search_field == 'date':
                queryset = queryset.filter(invoice_date__date__icontains=search_value)
            elif search_field == 'total':
                try:
                    total_val = Decimal(search_value)
                    queryset = queryset.filter(total=total_val)
                except Exception:
                    queryset = queryset.none()
            else:  # 'all'
                q_filters = Q(customer__first_name__icontains=search_value) | \
                            Q(customer__last_name__icontains=search_value) | \
                            Q(customer__dni__icontains=search_value) | \
                            Q(invoice_date__date__icontains=search_value)
                
                if search_value.isdigit():
                    q_filters |= Q(id=int(search_value))
                
                try:
                    total_val = Decimal(search_value)
                    q_filters |= Q(total=total_val)
                except Exception:
                    pass
                
                queryset = queryset.filter(q_filters)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context

class InvoiceCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'billing.add_invoice'
    def get(self, request, *args, **kwargs):
        customers = Customer.objects.filter(is_active=True).select_related('profile')
        products = Product.objects.filter(is_active=True).select_related('brand', 'group')
        
        customers_json = []
        for c in customers:
            taxpayer_type = 'final'
            payment_terms = 'cash'
            if hasattr(c, 'profile'):
                taxpayer_type = c.profile.taxpayer_type
                payment_terms = c.profile.payment_terms
            
            customers_json.append({
                'id': c.id,
                'dni': c.dni,
                'first_name': c.first_name,
                'last_name': c.last_name,
                'email': c.email or '',
                'phone': c.phone or '',
                'address': c.address or '',
                'taxpayer_type': taxpayer_type,
                'payment_terms': payment_terms
            })
            
        products_json = []
        for p in products:
            products_json.append({
                'id': p.id,
                'name': f"{p.name} ({p.brand.name})",
                'price': float(p.unit_price),
                'stock': p.stock
            })
            
        context = {
            'title': 'Crear Factura',
            'customers': customers,
            'products': products,
            'customers_json_str': json.dumps(customers_json),
            'products_json_str': json.dumps(products_json),
        }
        return render(request, 'billing/invoice_form.html', context)
        
    def post(self, request, *args, **kwargs):
        customer_id = request.POST.get('customer_select', '').strip()
        customer_dni = request.POST.get('customer_dni', '').strip()
        customer_first_name = request.POST.get('customer_first_name', '').strip()
        customer_last_name = request.POST.get('customer_last_name', '').strip()
        customer_email = request.POST.get('customer_email', '').strip() or None
        customer_phone = request.POST.get('customer_phone', '').strip() or None
        customer_address = request.POST.get('customer_address', '').strip() or None
        customer_taxpayer_type = request.POST.get('customer_taxpayer_type', 'final')
        customer_payment_terms = request.POST.get('customer_payment_terms', 'cash')
        
        product_ids = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')
        
        errors = []
        if not customer_id:
            errors.append("Debe seleccionar un cliente o elegir '-- Nuevo Cliente --'.")
        
        if customer_id == 'new' or not customer_id:
            if not customer_dni:
                errors.append("El DNI/RUC es obligatorio para un nuevo cliente.")
            else:
                if not re.match(r'^\d+$', customer_dni):
                    errors.append("La identificación (DNI/RUC) solo debe contener números.")
                elif len(customer_dni) not in [10, 13]:
                    errors.append("La identificación debe tener exactamente 10 (DNI) o 13 (RUC) dígitos.")
            if not customer_first_name or not customer_last_name:
                errors.append("El Nombre y Apellido son obligatorios.")
            if customer_phone:
                phone_cleaned = re.sub(r'\s+|-', '', customer_phone)
                if not re.match(r'^\d+$', phone_cleaned):
                    errors.append("El teléfono solo debe contener números.")
                
        if not product_ids:
            errors.append("Debe agregar al menos un producto a la factura.")
            
        if len(product_ids) != len(quantities) or len(product_ids) != len(prices):
            errors.append("Datos de productos incorrectos.")
            
        items_to_save = []
        subtotal = Decimal('0.00')
        
        for idx in range(len(product_ids)):
            p_id = product_ids[idx]
            qty_str = quantities[idx]
            price_str = prices[idx]
            
            if not p_id or not qty_str or not price_str:
                errors.append(f"Fila {idx+1}: Complete todos los campos del producto.")
                continue
                
            try:
                qty = int(qty_str)
                price = Decimal(price_str)
            except (ValueError, TypeError):
                errors.append(f"Fila {idx+1}: Cantidad o precio no válidos.")
                continue
                
            if qty <= 0:
                errors.append(f"Fila {idx+1}: La cantidad debe ser mayor que cero.")
                continue
                
            if price < 0:
                errors.append(f"Fila {idx+1}: El precio no puede ser negativo.")
                continue
                
            product = Product.objects.filter(id=p_id).first()
            if not product:
                errors.append(f"Fila {idx+1}: El producto seleccionado no existe.")
                continue
                
            if product.stock < qty:
                errors.append(f"Stock insuficiente para {product.name}. Stock disponible: {product.stock}.")
                continue
                
            line_subtotal = qty * price
            subtotal += line_subtotal
            items_to_save.append({
                'product': product,
                'quantity': qty,
                'unit_price': price,
                'subtotal': line_subtotal
            })
            
        if errors:
            for err in errors:
                messages.error(request, err)
            return self._render_form_with_errors(request)
            
        try:
            with transaction.atomic():
                if customer_id and customer_id != 'new':
                    customer = Customer.objects.get(id=customer_id)
                    customer.first_name = customer_first_name
                    customer.last_name = customer_last_name
                    customer.email = customer_email
                    customer.phone = customer_phone
                    customer.address = customer_address
                    customer.save()
                else:
                    customer = Customer.objects.filter(dni=customer_dni).first()
                    if customer:
                        customer.first_name = customer_first_name
                        customer.last_name = customer_last_name
                        customer.email = customer_email
                        customer.phone = customer_phone
                        customer.address = customer_address
                        customer.save()
                    else:
                        customer = Customer.objects.create(
                            dni=customer_dni,
                            first_name=customer_first_name,
                            last_name=customer_last_name,
                            email=customer_email,
                            phone=customer_phone,
                            address=customer_address
                        )
                
                profile, created = CustomerProfile.objects.get_or_create(customer=customer)
                profile.taxpayer_type = customer_taxpayer_type
                profile.payment_terms = customer_payment_terms
                profile.save()
                
                tax = subtotal * Decimal('0.15')
                total = subtotal + tax
                
                invoice = Invoice.objects.create(
                    customer=customer,
                    subtotal=subtotal,
                    tax=tax,
                    total=total,
                    is_active=True
                )
                
                for item in items_to_save:
                    InvoiceDetail.objects.create(
                        invoice=invoice,
                        product=item['product'],
                        quantity=item['quantity'],
                        unit_price=item['unit_price'],
                        subtotal=item['subtotal']
                    )
                    item['product'].stock -= item['quantity']
                    item['product'].save()
                    
            # Enviar correo al cliente si tiene email registrado
            if customer.email:
                try:
                    from django.core.mail import EmailMessage
                    pdf_data = generate_invoice_pdf_data(invoice)
                    email = EmailMessage(
                        subject=f'Factura #{invoice.id} - Sistema de Ventas',
                        body=(
                            f'Hola {customer.full_name},\n\n'
                            f'Se ha generado la factura #{invoice.id} de su compra realizada el {invoice.invoice_date.strftime("%d/%m/%Y")}.\n'
                            f'Adjunto a este correo encontrará el documento PDF con el detalle correspondiente.\n\n'
                            f'Detalles de facturación:\n'
                            f'- Subtotal: ${invoice.subtotal}\n'
                            f'- IVA (15%): ${invoice.tax}\n'
                            f'- Total Facturado: ${invoice.total}\n\n'
                            f'Agradecemos su preferencia.\n'
                            f'Atentamente,\nEl equipo de Ventas'
                        ),
                        from_email=None,
                        to=[customer.email]
                    )
                    email.attach(f'Factura_{invoice.id}.pdf', pdf_data, 'application/pdf')
                    email.send(fail_silently=False)
                    messages.success(request, f"Factura enviada automáticamente al correo: {customer.email}")
                except Exception as mail_err:
                    messages.warning(request, f"La factura fue guardada, pero no pudo ser enviada por correo: {str(mail_err)}")

            messages.success(request, f"Factura #{invoice.id} guardada con éxito.")
            return redirect('billing:invoice_list')
            
        except Exception as e:
            messages.error(request, f"Error al guardar la factura: {str(e)}")
            return self._render_form_with_errors(request)

    def _render_form_with_errors(self, request):
        customers = Customer.objects.filter(is_active=True).select_related('profile')
        products = Product.objects.filter(is_active=True).select_related('brand', 'group')
        
        customers_json = []
        for c in customers:
            taxpayer_type = 'final'
            payment_terms = 'cash'
            if hasattr(c, 'profile'):
                taxpayer_type = c.profile.taxpayer_type
                payment_terms = c.profile.payment_terms
            
            customers_json.append({
                'id': c.id,
                'dni': c.dni,
                'first_name': c.first_name,
                'last_name': c.last_name,
                'email': c.email or '',
                'phone': c.phone or '',
                'address': c.address or '',
                'taxpayer_type': taxpayer_type,
                'payment_terms': payment_terms
            })
            
        products_json = []
        for p in products:
            products_json.append({
                'id': p.id,
                'name': f"{p.name} ({p.brand.name})",
                'price': float(p.unit_price),
                'stock': p.stock
            })
            
        product_ids = request.POST.getlist('product[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')
        
        selected_items = []
        for idx in range(len(product_ids)):
            try:
                selected_items.append({
                    'product_id': int(product_ids[idx]) if product_ids[idx] else '',
                    'quantity': int(quantities[idx]) if quantities[idx] else 1,
                    'price': float(prices[idx]) if prices[idx] else 0.00
                })
            except (ValueError, TypeError):
                selected_items.append({
                    'product_id': product_ids[idx],
                    'quantity': quantities[idx],
                    'price': prices[idx]
                })

        posted_values = {
            'customer_select': request.POST.get('customer_select', ''),
            'customer_dni': request.POST.get('customer_dni', ''),
            'customer_first_name': request.POST.get('customer_first_name', ''),
            'customer_last_name': request.POST.get('customer_last_name', ''),
            'customer_email': request.POST.get('customer_email', '') or '',
            'customer_phone': request.POST.get('customer_phone', '') or '',
            'customer_address': request.POST.get('customer_address', '') or '',
            'customer_taxpayer_type': request.POST.get('customer_taxpayer_type', 'final'),
            'customer_payment_terms': request.POST.get('customer_payment_terms', 'cash'),
        }

        context = {
            'title': 'Crear Factura',
            'customers': customers,
            'products': products,
            'customers_json_str': json.dumps(customers_json),
            'products_json_str': json.dumps(products_json),
            'posted_values_json': json.dumps(posted_values),
            'selected_items_json': json.dumps(selected_items),
        }
        return render(request, 'billing/invoice_form.html', context)
class InvoiceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, StaffRequiredMixin, DeleteView):
    permission_required = 'billing.delete_invoice'
    model = Invoice
    template_name = 'billing/invoice_confirm_delete.html'
    success_url = reverse_lazy('billing:invoice_list')
    staff_redirect_url = '/invoices/'

# === REPORTES DE PRODUCTOS (Excel / PDF) ===
@login_required
@permission_required('billing.view_product')
def product_report_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Productos"
    
    ws.merge_cells("A1:F1")
    ws["A1"] = "REPORTE GENERAL DE PRODUCTOS"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40
    
    headers = ["Nombre del Producto", "Marca", "Categoría/Grupo", "Precio Unitario (USD)", "Stock", "Balance (USD)"]
    ws.append([])
    ws.append(headers)
    
    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    
    for col in range(1, 7):
        cell = ws.cell(row=3, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
    ws.row_dimensions[3].height = 25
    
    products = Product.objects.all().order_by('name')
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    
    for p in products:
        row = [
            p.name,
            p.brand.name if p.brand else "-",
            p.group.name if p.group else "-",
            float(p.unit_price),
            p.stock,
            float(p.balance)
        ]
        ws.append(row)
        curr_row = ws.max_row
        ws.row_dimensions[curr_row].height = 20
        
        ws.cell(row=curr_row, column=1).alignment = left_align
        ws.cell(row=curr_row, column=2).alignment = left_align
        ws.cell(row=curr_row, column=3).alignment = left_align
        
        price_cell = ws.cell(row=curr_row, column=4)
        price_cell.alignment = right_align
        price_cell.number_format = '$#,##0.00'
        
        stock_cell = ws.cell(row=curr_row, column=5)
        stock_cell.alignment = right_align
        stock_cell.number_format = '#,##0'

        balance_cell = ws.cell(row=curr_row, column=6)
        balance_cell.alignment = right_align
        balance_cell.number_format = '$#,##0.00'
        
        for col in range(1, 7):
            c = ws.cell(row=curr_row, column=col)
            c.font = Font(name="Calibri", size=11)
            c.border = thin_border
            
    ws.auto_filter.ref = f"A3:F{ws.max_row}"
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            val_str = str(cell.value or '')
            if cell.column in [4, 6] and isinstance(cell.value, (int, float)):
                val_str = f"${cell.value:,.2f}"
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
        
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="Reporte_Productos.xlsx"'
    wb.save(response)
    return response

@login_required
@permission_required('billing.view_product')
def product_report_pdf(request):
    import io
    import datetime
    from django.http import FileResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfgen import canvas
    
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_number(num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def draw_page_number(self, page_count):
            self.saveState()
            self.setFont("Helvetica", 9)
            self.setFillColor(colors.HexColor("#7F7F7F"))
            self.setStrokeColor(colors.HexColor("#D9D9D9"))
            self.setLineWidth(0.5)
            self.line(36, 756, 576, 756)
            self.drawString(36, 762, "Sistema de Ventas - Reporte de Productos")
            self.line(36, 54, 576, 54)
            page_text = f"Página {self._pageNumber} de {page_count}"
            self.drawRightString(576, 42, page_text)
            self.drawString(36, 42, "Reporte generado automáticamente")
            self.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=72
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#595959"),
        spaceAfter=25
    )
    cell_header_style = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white,
        alignment=1
    )
    cell_text_left = ParagraphStyle(
        'CellTextLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor("#262626")
    )
    cell_text_right = ParagraphStyle(
        'CellTextRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor("#262626"),
        alignment=2
    )
    
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("REPORTE GENERAL DE PRODUCTOS", title_style))
    story.append(Paragraph(f"Fecha de Generación: {now_str} | Total de productos registrados en base de datos.", subtitle_style))
    
    products = Product.objects.all().order_by('name')
    
    data = [
        [
            Paragraph("Nombre del Producto", cell_header_style),
            Paragraph("Marca", cell_header_style),
            Paragraph("Categoría", cell_header_style),
            Paragraph("Precio (USD)", cell_header_style),
            Paragraph("Stock", cell_header_style),
            Paragraph("Balance (USD)", cell_header_style)
        ]
    ]
    
    for p in products:
        data.append([
            Paragraph(p.name, cell_text_left),
            Paragraph(p.brand.name if p.brand else "-", cell_text_left),
            Paragraph(p.group.name if p.group else "-", cell_text_left),
            Paragraph(f"${p.unit_price:,.2f}", cell_text_right),
            Paragraph(f"{p.stock:,}", cell_text_right),
            Paragraph(f"${p.balance:,.2f}", cell_text_right)
        ])
        
    col_widths = [140, 80, 80, 80, 80, 80]
    
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2F5597")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F2F4F7"), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    story.append(t)
    doc.build(story, canvasmaker=NumberedCanvas)
    
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="Reporte_Productos.pdf")


# === REPORTES DE MARCAS (Excel / PDF) ===
@login_required
@permission_required('billing.view_brand')
def brand_report_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Marcas"
    ws.merge_cells("A1:D1")
    ws["A1"] = "REPORTE GENERAL DE MARCAS"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40

    headers = ["ID", "Nombre de Marca", "Descripción", "Estado"]
    ws.append([])
    ws.append(headers)

    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for col in range(1, 5):
        cell = ws.cell(row=3, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 25

    brands = Brand.objects.all().order_by('name')
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    for b in brands:
        row = [
            b.id,
            b.name,
            b.description or "",
            "Activo" if b.is_active else "Inactivo"
        ]
        ws.append(row)
        curr_row = ws.max_row
        ws.row_dimensions[curr_row].height = 20
        ws.cell(row=curr_row, column=1).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=4).alignment = Alignment(horizontal="center")
        for col in range(1, 5):
            c = ws.cell(row=curr_row, column=col)
            c.font = Font(name="Calibri", size=11)
            c.border = thin_border

    ws.auto_filter.ref = f"A3:D{ws.max_row}"
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="Reporte_Marcas.xlsx"'
    wb.save(response)
    return response


@login_required
@permission_required('billing.view_brand')
def brand_report_pdf(request):
    import io
    import datetime
    from django.http import FileResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=72
    )

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#595959"),
        spaceAfter=25
    )
    cell_header_style = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white,
        alignment=1
    )
    cell_text_left = ParagraphStyle(
        'CellTextLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor("#262626")
    )
    cell_text_center = ParagraphStyle(
        'CellTextCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor("#262626"),
        alignment=1
    )

    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("REPORTE GENERAL DE MARCAS", title_style))
    story.append(Paragraph(f"Fecha de Generación: {now_str} | Total de marcas registradas.", subtitle_style))

    brands = Brand.objects.all().order_by('name')

    data = [
        [
            Paragraph("ID", cell_header_style),
            Paragraph("Nombre de Marca", cell_header_style),
            Paragraph("Descripción", cell_header_style),
            Paragraph("Estado", cell_header_style)
        ]
    ]

    for b in brands:
        data.append([
            Paragraph(f"#{b.id}", cell_text_center),
            Paragraph(b.name, cell_text_left),
            Paragraph(b.description or "", cell_text_left),
            Paragraph("Activo" if b.is_active else "Inactivo", cell_text_center)
        ])

    col_widths = [50, 150, 240, 100]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2F5597")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F2F4F7"), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))

    story.append(t)
    doc.build(story, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="Reporte_Marcas.pdf")


# === REPORTES DE CATEGORIAS / GRUPOS (Excel / PDF) ===
@login_required
@permission_required('billing.view_productgroup')
def productgroup_report_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Grupos"
    ws.merge_cells("A1:C1")
    ws["A1"] = "REPORTE GENERAL DE GRUPOS DE PRODUCTOS"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40

    headers = ["ID", "Nombre de Grupo", "Estado"]
    ws.append([])
    ws.append(headers)

    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for col in range(1, 4):
        cell = ws.cell(row=3, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 25

    groups = ProductGroup.objects.all().order_by('name')
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    for g in groups:
        row = [
            g.id,
            g.name,
            "Activo" if g.is_active else "Inactivo"
        ]
        ws.append(row)
        curr_row = ws.max_row
        ws.row_dimensions[curr_row].height = 20
        ws.cell(row=curr_row, column=1).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=3).alignment = Alignment(horizontal="center")
        for col in range(1, 4):
            c = ws.cell(row=curr_row, column=col)
            c.font = Font(name="Calibri", size=11)
            c.border = thin_border

    ws.auto_filter.ref = f"A3:C{ws.max_row}"
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="Reporte_Grupos.xlsx"'
    wb.save(response)
    return response


@login_required
@permission_required('billing.view_productgroup')
def productgroup_report_pdf(request):
    import io
    import datetime
    from django.http import FileResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=72
    )

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#595959"),
        spaceAfter=25
    )
    cell_header_style = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white,
        alignment=1
    )
    cell_text_left = ParagraphStyle(
        'CellTextLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor("#262626")
    )
    cell_text_center = ParagraphStyle(
        'CellTextCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor("#262626"),
        alignment=1
    )

    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("REPORTE GENERAL DE GRUPOS DE PRODUCTOS", title_style))
    story.append(Paragraph(f"Fecha de Generación: {now_str} | Total de categorías/grupos registrados.", subtitle_style))

    groups = ProductGroup.objects.all().order_by('name')

    data = [
        [
            Paragraph("ID", cell_header_style),
            Paragraph("Nombre de Grupo", cell_header_style),
            Paragraph("Estado", cell_header_style)
        ]
    ]

    for g in groups:
        data.append([
            Paragraph(f"#{g.id}", cell_text_center),
            Paragraph(g.name, cell_text_left),
            Paragraph("Activo" if g.is_active else "Inactivo", cell_text_center)
        ])

    col_widths = [80, 320, 140]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2F5597")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F2F4F7"), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))

    story.append(t)
    doc.build(story, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="Reporte_Grupos.pdf")


# === REPORTES DE PROVEEDORES (Excel / PDF) ===
@login_required
@permission_required('billing.view_supplier')
def supplier_report_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Proveedores"
    ws.merge_cells("A1:G1")
    ws["A1"] = "REPORTE GENERAL DE PROVEEDORES"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40

    headers = ["ID", "Razón Social", "Contacto", "Email", "Teléfono", "Dirección", "Estado"]
    ws.append([])
    ws.append(headers)

    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for col in range(1, 8):
        cell = ws.cell(row=3, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 25

    suppliers = Supplier.objects.all().order_by('name')
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    for s in suppliers:
        row = [
            s.id,
            s.name,
            s.contact_name or "",
            s.email or "",
            s.phone or "",
            s.address or "",
            "Activo" if s.is_active else "Inactivo"
        ]
        ws.append(row)
        curr_row = ws.max_row
        ws.row_dimensions[curr_row].height = 20
        ws.cell(row=curr_row, column=1).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=7).alignment = Alignment(horizontal="center")
        for col in range(1, 8):
            c = ws.cell(row=curr_row, column=col)
            c.font = Font(name="Calibri", size=11)
            c.border = thin_border

    ws.auto_filter.ref = f"A3:G{ws.max_row}"
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="Reporte_Proveedores.xlsx"'
    wb.save(response)
    return response


@login_required
@permission_required('billing.view_supplier')
def supplier_report_pdf(request):
    import io
    import datetime
    from django.http import FileResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=72
    )

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#595959"),
        spaceAfter=25
    )
    cell_header_style = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white,
        alignment=1
    )
    cell_text_left = ParagraphStyle(
        'CellTextLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor("#262626")
    )
    cell_text_center = ParagraphStyle(
        'CellTextCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor("#262626"),
        alignment=1
    )

    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("REPORTE GENERAL DE PROVEEDORES", title_style))
    story.append(Paragraph(f"Fecha de Generación: {now_str} | Total de proveedores registrados.", subtitle_style))

    suppliers = Supplier.objects.all().order_by('name')

    data = [
        [
            Paragraph("ID", cell_header_style),
            Paragraph("Razón Social", cell_header_style),
            Paragraph("Contacto", cell_header_style),
            Paragraph("Email", cell_header_style),
            Paragraph("Teléfono", cell_header_style),
            Paragraph("Estado", cell_header_style)
        ]
    ]

    for s in suppliers:
        data.append([
            Paragraph(f"#{s.id}", cell_text_center),
            Paragraph(s.name, cell_text_left),
            Paragraph(s.contact_name or "", cell_text_left),
            Paragraph(s.email or "", cell_text_left),
            Paragraph(s.phone or "", cell_text_center),
            Paragraph("Activo" if s.is_active else "Inactivo", cell_text_center)
        ])

    col_widths = [40, 140, 100, 130, 80, 50]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2F5597")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F2F4F7"), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))

    story.append(t)
    doc.build(story, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="Reporte_Proveedores.pdf")


# === REPORTES DE CLIENTES (Excel / PDF) ===
@login_required
@permission_required('billing.view_customer')
def customer_report_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clientes"
    ws.merge_cells("A1:G1")
    ws["A1"] = "REPORTE GENERAL DE CLIENTES"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40

    headers = ["ID", "DNI/RUC", "Nombre Completo", "Email", "Teléfono", "Dirección", "Estado"]
    ws.append([])
    ws.append(headers)

    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for col in range(1, 8):
        cell = ws.cell(row=3, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 25

    customers = Customer.objects.all().order_by('last_name', 'first_name')
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    for c in customers:
        row = [
            c.id,
            c.dni,
            c.full_name,
            c.email or "",
            c.phone or "",
            c.address or "",
            "Activo" if c.is_active else "Inactivo"
        ]
        ws.append(row)
        curr_row = ws.max_row
        ws.row_dimensions[curr_row].height = 20
        ws.cell(row=curr_row, column=1).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=2).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=7).alignment = Alignment(horizontal="center")
        for col in range(1, 8):
            cell_obj = ws.cell(row=curr_row, column=col)
            cell_obj.font = Font(name="Calibri", size=11)
            cell_obj.border = thin_border

    ws.auto_filter.ref = f"A3:G{ws.max_row}"
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            val_str = str(cell.value or '')
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="Reporte_Clientes.xlsx"'
    wb.save(response)
    return response


@login_required
@permission_required('billing.view_customer')
def customer_report_pdf(request):
    import io
    import datetime
    from django.http import FileResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=72
    )

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#595959"),
        spaceAfter=25
    )
    cell_header_style = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white,
        alignment=1
    )
    cell_text_left = ParagraphStyle(
        'CellTextLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor("#262626")
    )
    cell_text_center = ParagraphStyle(
        'CellTextCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor("#262626"),
        alignment=1
    )

    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("REPORTE GENERAL DE CLIENTES", title_style))
    story.append(Paragraph(f"Fecha de Generación: {now_str} | Total de clientes registrados.", subtitle_style))

    customers = Customer.objects.all().order_by('last_name', 'first_name')

    data = [
        [
            Paragraph("DNI/RUC", cell_header_style),
            Paragraph("Nombre Completo", cell_header_style),
            Paragraph("Email", cell_header_style),
            Paragraph("Teléfono", cell_header_style),
            Paragraph("Dirección", cell_header_style),
            Paragraph("Estado", cell_header_style)
        ]
    ]

    for c in customers:
        data.append([
            Paragraph(c.dni, cell_text_center),
            Paragraph(c.full_name, cell_text_left),
            Paragraph(c.email or "", cell_text_left),
            Paragraph(c.phone or "", cell_text_center),
            Paragraph(c.address or "", cell_text_left),
            Paragraph("Activo" if c.is_active else "Inactivo", cell_text_center)
        ])

    col_widths = [90, 140, 130, 80, 55, 45]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2F5597")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F2F4F7"), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))

    story.append(t)
    doc.build(story, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="Reporte_Clientes.pdf")


# === REPORTES DE FACTURAS (Excel / PDF) ===
@login_required
@permission_required('billing.view_invoice')
def invoice_report_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from django.http import HttpResponse

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Facturas"
    ws.merge_cells("A1:G1")
    ws["A1"] = "REPORTE GENERAL DE FACTURAS EMITIDAS"
    ws["A1"].font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40

    headers = ["ID Factura", "Cliente", "Fecha de Emisión", "Subtotal (USD)", "IVA (15%)", "Total (USD)", "Estado"]
    ws.append([])
    ws.append(headers)

    header_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    for col in range(1, 8):
        cell = ws.cell(row=3, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 25

    invoices = Invoice.objects.select_related('customer').all().order_by('-invoice_date')
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    for i in invoices:
        row = [
            i.id,
            i.customer.full_name,
            i.invoice_date.strftime("%d/%m/%Y %H:%M"),
            float(i.subtotal),
            float(i.tax),
            float(i.total),
            "Activo" if i.is_active else "Anulado"
        ]
        ws.append(row)
        curr_row = ws.max_row
        ws.row_dimensions[curr_row].height = 20
        ws.cell(row=curr_row, column=1).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=3).alignment = Alignment(horizontal="center")
        ws.cell(row=curr_row, column=7).alignment = Alignment(horizontal="center")
        
        ws.cell(row=curr_row, column=4).number_format = '$#,##0.00'
        ws.cell(row=curr_row, column=5).number_format = '$#,##0.00'
        ws.cell(row=curr_row, column=6).number_format = '$#,##0.00'
        ws.cell(row=curr_row, column=4).alignment = Alignment(horizontal="right")
        ws.cell(row=curr_row, column=5).alignment = Alignment(horizontal="right")
        ws.cell(row=curr_row, column=6).alignment = Alignment(horizontal="right")

        for col in range(1, 8):
            c = ws.cell(row=curr_row, column=col)
            c.font = Font(name="Calibri", size=11)
            c.border = thin_border

    ws.auto_filter.ref = f"A3:G{ws.max_row}"
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            val_str = str(cell.value or '')
            if cell.column in [4, 5, 6] and isinstance(cell.value, (int, float)):
                val_str = f"${cell.value:,.2f}"
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="Reporte_Facturas.xlsx"'
    wb.save(response)
    return response


@login_required
@permission_required('billing.view_invoice')
def invoice_report_pdf(request):
    import io
    import datetime
    from django.http import FileResponse
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=72
    )

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#595959"),
        spaceAfter=25
    )
    cell_header_style = ParagraphStyle(
        'CellHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.white,
        alignment=1
    )
    cell_text_left = ParagraphStyle(
        'CellTextLeft',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor("#262626")
    )
    cell_text_center = ParagraphStyle(
        'CellTextCenter',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor("#262626"),
        alignment=1
    )
    cell_text_right = ParagraphStyle(
        'CellTextRight',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor("#262626"),
        alignment=2
    )

    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph("REPORTE GENERAL DE FACTURAS", title_style))
    story.append(Paragraph(f"Fecha de Generación: {now_str} | Historial de facturas emitidas.", subtitle_style))

    invoices = Invoice.objects.select_related('customer').all().order_by('-invoice_date')

    data = [
        [
            Paragraph("Factura #", cell_header_style),
            Paragraph("Cliente", cell_header_style),
            Paragraph("Fecha de Emisión", cell_header_style),
            Paragraph("Subtotal", cell_header_style),
            Paragraph("IVA (15%)", cell_header_style),
            Paragraph("Total", cell_header_style),
            Paragraph("Estado", cell_header_style)
        ]
    ]

    for i in invoices:
        data.append([
            Paragraph(f"#{i.id}", cell_text_center),
            Paragraph(i.customer.full_name, cell_text_left),
            Paragraph(i.invoice_date.strftime("%d/%m/%Y %H:%M"), cell_text_center),
            Paragraph(f"${i.subtotal:,.2f}", cell_text_right),
            Paragraph(f"${i.tax:,.2f}", cell_text_right),
            Paragraph(f"${i.total:,.2f}", cell_text_right),
            Paragraph("Activo" if i.is_active else "Anulado", cell_text_center)
        ])

    col_widths = [55, 140, 95, 90, 50, 50, 60]

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2F5597")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor("#F2F4F7"), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9D9")),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))

    story.append(t)
    doc.build(story, canvasmaker=NumberedCanvas)

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="Reporte_Facturas.pdf")


def generate_invoice_pdf_data(invoice):
    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    story = []
    styles = getSampleStyleSheet()
    
    # Estilos Personalizados
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor("#1F4E78"),
        spaceAfter=5
    )
    normal_style = ParagraphStyle(
        'InvoiceNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#262626"),
        spaceAfter=3
    )
    bold_style = ParagraphStyle(
        'InvoiceBold',
        parent=normal_style,
        fontName='Helvetica-Bold'
    )
    
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white,
        alignment=1
    )
    
    cell_left = ParagraphStyle(
        'CellLeft',
        parent=normal_style,
        fontSize=9
    )
    cell_center = ParagraphStyle(
        'CellCenter',
        parent=normal_style,
        fontSize=9,
        alignment=1
    )
    cell_right = ParagraphStyle(
        'CellRight',
        parent=normal_style,
        fontSize=9,
        alignment=2
    )

    # Encabezado
    story.append(Paragraph("FACTURA DE VENTA", title_style))
    story.append(Paragraph(f"Factura Nº: {invoice.id}", bold_style))
    story.append(Paragraph(f"Fecha: {invoice.invoice_date.strftime('%d/%m/%Y %H:%M')}", normal_style))
    story.append(Spacer(1, 15))
    
    # Tabla de Datos Emisor / Receptor
    info_data = [
        [
            Paragraph("<b>EMISOR</b><br/><b>Empresa:</b> Sistema de Ventas<br/><b>Email:</b> ventas@sistema.com", normal_style),
            Paragraph(f"<b>CLIENTE</b><br/><b>Nombre:</b> {invoice.customer.full_name}<br/><b>DNI/RUC:</b> {invoice.customer.dni}<br/><b>Email:</b> {invoice.customer.email or '-'}<br/><b>Tlf:</b> {invoice.customer.phone or '-'}", normal_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[250, 250])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('PADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # Tabla de Productos
    table_data = [
        [
            Paragraph("Producto", header_style),
            Paragraph("Cant.", header_style),
            Paragraph("Precio Unitario", header_style),
            Paragraph("Subtotal", header_style)
        ]
    ]
    
    for detail in invoice.details.all():
        table_data.append([
            Paragraph(detail.product.name, cell_left),
            Paragraph(str(detail.quantity), cell_center),
            Paragraph(f"${detail.unit_price:,.2f}", cell_right),
            Paragraph(f"${detail.subtotal:,.2f}", cell_right)
        ])
        
    items_table = Table(table_data, colWidths=[260, 60, 90, 90])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1F4E78")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D9D9D9")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))
    
    # Tabla de Totales
    totals_data = [
        [Paragraph("", cell_left), Paragraph("Subtotal:", cell_right), Paragraph(f"${invoice.subtotal:,.2f}", cell_right)],
        [Paragraph("", cell_left), Paragraph("IVA (15%):", cell_right), Paragraph(f"${invoice.tax:,.2f}", cell_right)],
        [Paragraph("", cell_left), Paragraph("TOTAL:", ParagraphStyle('TBold', parent=cell_right, fontName='Helvetica-Bold')), Paragraph(f"${invoice.total:,.2f}", ParagraphStyle('TBold2', parent=cell_right, fontName='Helvetica-Bold'))]
    ]
    totals_table = Table(totals_data, colWidths=[320, 90, 90])
    totals_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEABOVE', (1,2), (2,2), 1, colors.HexColor("#1F4E78")),
    ]))
    story.append(totals_table)
    
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


@login_required
@permission_required('billing.view_invoice')
def invoice_pdf(request, pk):
    from django.http import HttpResponse
    invoice = get_object_or_404(Invoice, pk=pk)
    pdf_data = generate_invoice_pdf_data(invoice)
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Factura_{invoice.id}.pdf"'
    return response


