from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q, Sum
from decimal import Decimal

from billing.models import Invoice
from purchasing.models import Purchase
from .models import CobroFactura, PagoCompra
from .forms import CobroFacturaForm, PagoCompraForm

class PagosHomeView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'pagos.view_cobrofactura'
    template_name = 'pagos/pagos_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Facturas a crédito activas
        invoices_credito = Invoice.objects.filter(tipo_pago='CREDITO', is_active=True)
        
        context['total_pendientes_count'] = invoices_credito.filter(estado='PENDIENTE').count()
        context['total_pendientes_monto'] = invoices_credito.filter(estado='PENDIENTE').aggregate(Sum('saldo'))['saldo__sum'] or Decimal('0.00')
        
        context['total_pagadas_count'] = invoices_credito.filter(estado='PAGADA').count()
        
        # Cobros realizados
        cobros = CobroFactura.objects.all()
        context['total_cobros_count'] = cobros.count()
        context['total_cobros_monto'] = cobros.aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
        
        # Listados recientes
        context['recent_cobros'] = cobros.select_related('factura', 'factura__customer').order_by('-fecha', '-id')[:5]
        context['top_pending_invoices'] = invoices_credito.filter(estado='PENDIENTE').select_related('customer').order_by('-saldo')[:5]
        
        # Porcentaje cobrado
        total_credito_generado = invoices_credito.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
        if total_credito_generado > 0:
            context['porcentaje_cobrado'] = round((context['total_cobros_monto'] / total_credito_generado) * 100, 1)
        else:
            context['porcentaje_cobrado'] = 0.0
            
        return context

class FacturasPendientesListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'pagos.view_cobrofactura'
    model = Invoice
    template_name = 'pagos/pagos_list.html'
    context_object_name = 'items'
    paginate_by = 10

    def get_queryset(self):
        # Muestra únicamente facturas a CRÉDITO pendientes de cobro y activas
        queryset = Invoice.objects.filter(
            tipo_pago='CREDITO',
            estado='PENDIENTE',
            is_active=True
        ).select_related('customer')

        # Filtro de búsqueda
        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()

        if search_value:
            if search_field == 'id':
                if search_value.isdigit():
                    queryset = queryset.filter(id=int(search_value))
                else:
                    queryset = queryset.none()
            elif search_field == 'numero':
                queryset = queryset.filter(numero__icontains=search_value)
            elif search_field == 'customer_name':
                queryset = queryset.filter(
                    Q(customer__first_name__icontains=search_value) |
                    Q(customer__last_name__icontains=search_value)
                )
            elif search_field == 'customer_dni':
                queryset = queryset.filter(customer__dni__icontains=search_value)
            else:  # 'all'
                q_filters = (
                    Q(numero__icontains=search_value) |
                    Q(customer__first_name__icontains=search_value) |
                    Q(customer__last_name__icontains=search_value) |
                    Q(customer__dni__icontains=search_value)
                )
                if search_value.isdigit():
                    q_filters |= Q(id=int(search_value))
                queryset = queryset.filter(q_filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Facturas Pendientes de Cobro'
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context


class CobroFacturaCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'pagos.add_cobrofactura'
    model = CobroFactura
    form_class = CobroFacturaForm
    template_name = 'pagos/pagos_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.invoice = get_object_or_404(Invoice, pk=self.kwargs.get('invoice_id'))
        if not self.invoice.is_active or self.invoice.estado == 'ANULADA':
            messages.error(request, "No se puede cobrar una factura anulada o inactiva.")
            return redirect('pagos:facturas_pendientes')
        if self.invoice.estado == 'PAGADA':
            messages.warning(request, f"La factura {self.invoice.numero or self.invoice.id} ya se encuentra totalmente pagada.")
            return redirect('pagos:facturas_pendientes')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice'] = self.invoice
        context['title'] = f"Registrar Cobro - Factura #{self.invoice.numero or self.invoice.id}"
        context['action'] = 'create'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.factura = self.invoice
        return form

    def form_valid(self, form):
        form.instance.factura = self.invoice
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                messages.success(self.request, f"Abono de ${form.cleaned_data['valor']} registrado con éxito sobre la factura {self.invoice.numero or self.invoice.id}.")
                return response
        except ValidationError as e:
            if hasattr(e, 'message_dict'):
                for field, errors in e.message_dict.items():
                    for err in errors:
                        form.add_error(field if field != '__all__' else None, err)
            else:
                form.add_error(None, e.message)
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('pagos:historial_factura', kwargs={'invoice_id': self.invoice.id})


class CobroFacturaUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'pagos.change_cobrofactura'
    model = CobroFactura
    form_class = CobroFacturaForm
    template_name = 'pagos/pagos_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.factura.is_active or self.object.factura.estado == 'ANULADA':
            messages.error(request, "No se puede editar un cobro de una factura anulada o inactiva.")
            return redirect('pagos:historial_pagos')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice'] = self.object.factura
        context['title'] = f"Editar Cobro #{self.object.id} - Factura #{self.object.factura.numero or self.object.factura.id}"
        context['action'] = 'update'
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                messages.success(self.request, f"Cobro #{self.object.id} actualizado con éxito.")
                return response
        except ValidationError as e:
            if hasattr(e, 'message_dict'):
                for field, errors in e.message_dict.items():
                    for err in errors:
                        form.add_error(field if field != '__all__' else None, err)
            else:
                form.add_error(None, e.message)
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('pagos:historial_factura', kwargs={'invoice_id': self.object.factura.id})


class CobroFacturaDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'pagos.delete_cobrofactura'
    model = CobroFactura
    template_name = 'pagos/pagos_delete.html'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.factura.estado == 'PAGADA':
            messages.error(request, "No se puede eliminar un pago de una factura que está totalmente cancelada.")
            return redirect('pagos:historial_factura', invoice_id=self.object.factura.id)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Eliminar Cobro #{self.object.id}"
        context['invoice'] = self.object.factura
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        invoice_id = self.object.factura.id
        try:
            with transaction.atomic():
                self.object.delete()
                messages.success(request, "Abono eliminado con éxito y saldo pendiente actualizado.")
                return redirect('pagos:historial_factura', invoice_id=invoice_id)
        except ValidationError as e:
            messages.error(request, f"Error al eliminar el abono: {e.message}")
            return redirect('pagos:historial_factura', invoice_id=invoice_id)


class HistorialPagosListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'pagos.view_cobrofactura'
    model = CobroFactura
    template_name = 'pagos/historial_pagos.html'
    context_object_name = 'items'
    paginate_by = 10

    def get_queryset(self):
        queryset = CobroFactura.objects.select_related('factura', 'factura__customer')
        invoice_id = self.kwargs.get('invoice_id')
        if invoice_id:
            queryset = queryset.filter(factura_id=invoice_id)
        
        search_value = self.request.GET.get('search_value', '').strip()
        if search_value:
            queryset = queryset.filter(
                Q(factura__numero__icontains=search_value) |
                Q(factura__customer__first_name__icontains=search_value) |
                Q(factura__customer__last_name__icontains=search_value) |
                Q(observacion__icontains=search_value)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice_id = self.kwargs.get('invoice_id')
        if invoice_id:
            context['invoice'] = get_object_or_404(Invoice, pk=invoice_id)
            context['title'] = f"Historial de Cobros - Factura #{context['invoice'].numero or context['invoice'].id}"
        else:
            context['title'] = "Historial General de Cobros"
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context


class FacturasPagadasListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'pagos.view_cobrofactura'
    model = Invoice
    template_name = 'pagos/facturas_pagadas.html'
    context_object_name = 'items'
    paginate_by = 10

    def get_queryset(self):
        # Muestra únicamente facturas a CRÉDITO completamente canceladas y activas
        queryset = Invoice.objects.filter(
            tipo_pago='CREDITO',
            estado='PAGADA',
            is_active=True
        ).select_related('customer')

        # Filtro de búsqueda
        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()

        if search_value:
            if search_field == 'id':
                if search_value.isdigit():
                    queryset = queryset.filter(id=int(search_value))
                else:
                    queryset = queryset.none()
            elif search_field == 'numero':
                queryset = queryset.filter(numero__icontains=search_value)
            elif search_field == 'customer_name':
                queryset = queryset.filter(
                    Q(customer__first_name__icontains=search_value) |
                    Q(customer__last_name__icontains=search_value)
                )
            elif search_field == 'customer_dni':
                queryset = queryset.filter(customer__dni__icontains=search_value)
            else:  # 'all'
                q_filters = (
                    Q(numero__icontains=search_value) |
                    Q(customer__first_name__icontains=search_value) |
                    Q(customer__last_name__icontains=search_value) |
                    Q(customer__dni__icontains=search_value)
                )
                if search_value.isdigit():
                    q_filters |= Q(id=int(search_value))
                queryset = queryset.filter(q_filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Historial de Facturas Canceladas (Crédito)'
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context


# ==============================================================================
# PAGOS DE COMPRAS (CUENTAS POR PAGAR)
# ==============================================================================

class PagosComprasHomeView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'pagos.view_pagocompra'
    template_name = 'pagos/pagos_compras_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Compras a crédito activas
        purchases_credito = Purchase.objects.filter(tipo_pago='CREDITO', is_active=True)
        
        context['total_pendientes_count'] = purchases_credito.filter(estado='PENDIENTE').count()
        context['total_pendientes_monto'] = purchases_credito.filter(estado='PENDIENTE').aggregate(Sum('saldo'))['saldo__sum'] or Decimal('0.00')
        
        context['total_pagadas_count'] = purchases_credito.filter(estado='PAGADA').count()
        
        # Pagos realizados
        pagos = PagoCompra.objects.all()
        context['total_pagos_count'] = pagos.count()
        context['total_pagos_monto'] = pagos.aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
        
        # Listados recientes
        context['recent_pagos'] = pagos.select_related('compra', 'compra__supplier').order_by('-fecha', '-id')[:5]
        context['top_pending_purchases'] = purchases_credito.filter(estado='PENDIENTE').select_related('supplier').order_by('-saldo')[:5]
        
        # Porcentaje pagado
        total_credito_generado = purchases_credito.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
        if total_credito_generado > 0:
            context['porcentaje_pagado'] = round((context['total_pagos_monto'] / total_credito_generado) * 100, 1)
        else:
            context['porcentaje_pagado'] = 0.0
            
        return context


class ComprasPendientesListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'pagos.view_pagocompra'
    model = Purchase
    template_name = 'pagos/compras_list.html'
    context_object_name = 'items'
    paginate_by = 10

    def get_queryset(self):
        # Muestra únicamente compras a CRÉDITO pendientes de pago y activas
        queryset = Purchase.objects.filter(
            tipo_pago='CREDITO',
            estado='PENDIENTE',
            is_active=True
        ).select_related('supplier')

        # Filtro de búsqueda
        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()

        if search_value:
            if search_field == 'id':
                if search_value.isdigit():
                    queryset = queryset.filter(id=int(search_value))
                else:
                    queryset = queryset.none()
            elif search_field == 'numero':
                queryset = queryset.filter(document_number__icontains=search_value)
            elif search_field == 'supplier_name':
                queryset = queryset.filter(supplier__name__icontains=search_value)
            else:  # 'all'
                q_filters = (
                    Q(document_number__icontains=search_value) |
                    Q(supplier__name__icontains=search_value)
                )
                if search_value.isdigit():
                    q_filters |= Q(id=int(search_value))
                queryset = queryset.filter(q_filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Compras Pendientes de Pago'
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context


class ComprasPagadasListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'pagos.view_pagocompra'
    model = Purchase
    template_name = 'pagos/compras_pagadas.html'
    context_object_name = 'items'
    paginate_by = 10

    def get_queryset(self):
        queryset = Purchase.objects.filter(
            tipo_pago='CREDITO',
            estado='PAGADA',
            is_active=True
        ).select_related('supplier')

        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()

        if search_value:
            if search_field == 'id':
                if search_value.isdigit():
                    queryset = queryset.filter(id=int(search_value))
                else:
                    queryset = queryset.none()
            elif search_field == 'numero':
                queryset = queryset.filter(document_number__icontains=search_value)
            elif search_field == 'supplier_name':
                queryset = queryset.filter(supplier__name__icontains=search_value)
            else:  # 'all'
                q_filters = (
                    Q(document_number__icontains=search_value) |
                    Q(supplier__name__icontains=search_value)
                )
                if search_value.isdigit():
                    q_filters |= Q(id=int(search_value))
                queryset = queryset.filter(q_filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Historial de Compras Pagadas (Crédito)'
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        return context


class PagoCompraCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'pagos.add_pagocompra'
    model = PagoCompra
    form_class = PagoCompraForm
    template_name = 'pagos/pagos_compras_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.purchase = get_object_or_404(Purchase, pk=self.kwargs.get('purchase_id'))
        if not self.purchase.is_active or self.purchase.estado == 'ANULADA':
            messages.error(request, "No se puede pagar una compra anulada o inactiva.")
            return redirect('pagos:compras_pendientes')
        if self.purchase.estado == 'PAGADA':
            messages.warning(request, f"La compra {self.purchase.document_number} ya se encuentra totalmente pagada.")
            return redirect('pagos:compras_pendientes')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['purchase'] = self.purchase
        context['title'] = f"Registrar Pago - Compra #{self.purchase.document_number}"
        context['action'] = 'create'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.compra = self.purchase
        return form

    def form_valid(self, form):
        form.instance.compra = self.purchase
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                pago = self.object
                
                # WhatsApp simulation on server (just like sales)
                if self.purchase.supplier.phone:
                    try:
                        import logging
                        logger = logging.getLogger(__name__)
                        whatsapp_msg = self.purchase.whatsapp_message
                        whatsapp_phone = self.purchase.whatsapp_phone
                        logger.info(f"--- WHATSAPP SIMULADO ENVIADO A PROVEEDOR {whatsapp_phone} ---\n{whatsapp_msg}\n-------------------")
                        messages.info(self.request, f"WhatsApp (Simulado): Notificación de pago preparada para el proveedor al número {self.purchase.supplier.phone}")
                    except Exception as wa_err:
                        messages.warning(self.request, f"No se pudo simular el envío por WhatsApp: {str(wa_err)}")

                messages.success(self.request, f"Pago de ${pago.valor} registrado con éxito en la Compra #{self.purchase.document_number}.")
                return response
        except ValidationError as val_err:
            for field, errors in val_err.message_dict.items():
                for error in errors:
                    form.add_error(field if field != '__all__' else None, error)
            return self.form_invalid(form)
        except Exception as e:
            form.add_error(None, f"Error al guardar el pago: {str(e)}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('pagos:compras_pendientes')


class PagoCompraUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = 'pagos.change_pagocompra'
    model = PagoCompra
    form_class = PagoCompraForm
    template_name = 'pagos/pagos_compras_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(PagoCompra, pk=self.kwargs.get('pk'))
        if self.pago.compra.estado == 'PAGADA' and self.pago.compra.saldo == 0 and not self.pago.compra.is_active:
            messages.error(request, "No se puede editar un pago sobre una compra cancelada/inactiva.")
            return redirect('pagos:compras_pendientes')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['purchase'] = self.pago.compra
        context['title'] = f"Editar Pago - Compra #{self.pago.compra.document_number}"
        context['action'] = 'update'
        return context

    def form_valid(self, form):
        try:
            with transaction.atomic():
                response = super().form_valid(form)
                messages.success(self.request, f"Pago de ${self.object.valor} actualizado con éxito.")
                return response
        except ValidationError as val_err:
            for field, errors in val_err.message_dict.items():
                for error in errors:
                    form.add_error(field if field != '__all__' else None, error)
            return self.form_invalid(form)
        except Exception as e:
            form.add_error(None, f"Error al actualizar el pago: {str(e)}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('pagos:compras_pendientes')


class PagoCompraDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = 'pagos.delete_pagocompra'
    model = PagoCompra
    template_name = 'pagos/pago_compra_confirm_delete.html'
    success_url = reverse_lazy('pagos:compras_pendientes')

    def dispatch(self, request, *args, **kwargs):
        self.pago = get_object_or_404(PagoCompra, pk=self.kwargs.get('pk'))
        if self.pago.compra.estado == 'PAGADA':
            messages.error(request, "No se puede eliminar un pago de una compra que ya está totalmente cancelada.")
            return redirect('pagos:compras_pendientes')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pago'] = self.pago
        return context

    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                pago = self.get_object()
                valor = pago.valor
                doc_num = pago.compra.document_number
                response = super().post(request, *args, **kwargs)
                messages.success(request, f"Pago de ${valor} de la Compra #{doc_num} eliminado correctamente.")
                return response
        except ValidationError as val_err:
            messages.error(request, f"No se pudo eliminar el pago: {val_err.message}")
            return redirect('pagos:compras_pendientes')
        except Exception as e:
            messages.error(request, f"Error al eliminar el pago: {str(e)}")
            return redirect('pagos:compras_pendientes')


class HistorialPagosComprasListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'pagos.view_pagocompra'
    model = PagoCompra
    template_name = 'pagos/historial_pagos_compras.html'
    context_object_name = 'items'
    paginate_by = 10

    def get_queryset(self):
        queryset = PagoCompra.objects.select_related('compra', 'compra__supplier').all()
        
        # Filtro opcional por compra específica
        purchase_id = self.kwargs.get('purchase_id')
        if purchase_id:
            queryset = queryset.filter(compra_id=purchase_id)

        # Filtro de búsqueda
        search_field = self.request.GET.get('search_field', 'all').strip()
        search_value = self.request.GET.get('search_value', '').strip()

        if search_value:
            if search_field == 'id':
                if search_value.isdigit():
                    queryset = queryset.filter(id=int(search_value))
                else:
                    queryset = queryset.none()
            elif search_field == 'numero':
                queryset = queryset.filter(compra__document_number__icontains=search_value)
            elif search_field == 'supplier_name':
                queryset = queryset.filter(compra__supplier__name__icontains=search_value)
            else:  # 'all'
                q_filters = (
                    Q(compra__document_number__icontains=search_value) |
                    Q(compra__supplier__name__icontains=search_value)
                )
                if search_value.isdigit():
                    q_filters |= Q(id=int(search_value))
                queryset = queryset.filter(q_filters)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Historial de Pagos a Proveedores'
        context['search_field'] = self.request.GET.get('search_field', 'all').strip()
        context['search_value'] = self.request.GET.get('search_value', '').strip()
        
        purchase_id = self.kwargs.get('purchase_id')
        if purchase_id:
            context['purchase_filter'] = get_object_or_404(Purchase, pk=purchase_id)
        return context

