from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth import login
from .models import *
from .forms import SignUpForm, BrandForm

# === REGISTRO ===
class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('billing:brand_list')
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

# === BRAND (FBV) ===
@login_required
def brand_list(request):
    brands = Brand.objects.all()
    return render(request, 'billing/brand_list.html', {'brands': brands})

@login_required
def brand_create(request):
    if request.method == 'POST':
        form = BrandForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Brand created!')
            return redirect('billing:brand_list')
    else: form = BrandForm()
    return render(request, 'billing/brand_form.html', {'form':form, 'title':'Create Brand'})

@login_required
def brand_update(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        form = BrandForm(request.POST, instance=brand)
        if form.is_valid():
            form.save()
            messages.success(request, 'Brand updated!')
            return redirect('billing:brand_list')
    else: form = BrandForm(instance=brand)
    return render(request, 'billing/brand_form.html', {'form':form, 'title':'Edit Brand'})

@login_required
def brand_delete(request, pk):
    brand = get_object_or_404(Brand, pk=pk)
    if request.method == 'POST':
        brand.delete()
        messages.success(request, 'Brand deleted!')
        return redirect('billing:brand_list')
    return render(request, 'billing/brand_confirm_delete.html', {'object': brand})

# === PRODUCTGROUP (CBV) ===
class ProductGroupListView(LoginRequiredMixin, ListView):
    model = ProductGroup; template_name = 'billing/productgroup_list.html'; context_object_name = 'items'
class ProductGroupCreateView(LoginRequiredMixin, CreateView):
    model = ProductGroup; fields = ['name','is_active']; template_name = 'billing/productgroup_form.html'; success_url = reverse_lazy('billing:productgroup_list')
class ProductGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = ProductGroup; fields = ['name','is_active']; template_name = 'billing/productgroup_form.html'; success_url = reverse_lazy('billing:productgroup_list')
class ProductGroupDeleteView(LoginRequiredMixin, DeleteView):
    model = ProductGroup; template_name = 'billing/productgroup_confirm_delete.html'; success_url = reverse_lazy('billing:productgroup_list')

# === SUPPLIER (CBV) ===
class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier; template_name = 'billing/supplier_list.html'; context_object_name = 'items'
class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier; fields = ['name','contact_name','email','phone','address','is_active']; template_name = 'billing/supplier_form.html'; success_url = reverse_lazy('billing:supplier_list')
class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier; fields = ['name','contact_name','email','phone','address','is_active']; template_name = 'billing/supplier_form.html'; success_url = reverse_lazy('billing:supplier_list')
class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    model = Supplier; template_name = 'billing/supplier_confirm_delete.html'; success_url = reverse_lazy('billing:supplier_list')

# === PRODUCT (CBV) ===
class ProductListView(LoginRequiredMixin, ListView):
    model = Product; template_name = 'billing/product_list.html'; context_object_name = 'items'
class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product; fields = ['name','description','brand','group','suppliers','unit_price','stock','is_active']; template_name = 'billing/product_form.html'; success_url = reverse_lazy('billing:product_list')
class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product; fields = ['name','description','brand','group','suppliers','unit_price','stock','is_active']; template_name = 'billing/product_form.html'; success_url = reverse_lazy('billing:product_list')
class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product; template_name = 'billing/product_confirm_delete.html'; success_url = reverse_lazy('billing:product_list')

# === CUSTOMER (CBV) ===
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer; template_name = 'billing/customer_list.html'; context_object_name = 'items'
class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer; fields = ['dni','first_name','last_name','email','phone','address','is_active']; template_name = 'billing/customer_form.html'; success_url = reverse_lazy('billing:customer_list')
class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer; fields = ['dni','first_name','last_name','email','phone','address','is_active']; template_name = 'billing/customer_form.html'; success_url = reverse_lazy('billing:customer_list')
class CustomerDeleteView(LoginRequiredMixin, DeleteView):
    model = Customer; template_name = 'billing/customer_confirm_delete.html'; success_url = reverse_lazy('billing:customer_list')

# === INVOICE (CBV) ===
class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice; template_name = 'billing/invoice_list.html'; context_object_name = 'items'
class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice; fields = ['customer']; template_name = 'billing/invoice_form.html'; success_url = reverse_lazy('billing:invoice_list')
class InvoiceDeleteView(LoginRequiredMixin, DeleteView):
    model = Invoice; template_name = 'billing/invoice_confirm_delete.html'; success_url = reverse_lazy('billing:invoice_list')
