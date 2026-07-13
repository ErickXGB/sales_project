from django.urls import path
from . import views

app_name = 'pagos'

urlpatterns = [
    path('', views.PagosHomeView.as_view(), name='pagos_home'),
    path('list/', views.FacturasPendientesListView.as_view(), name='facturas_pendientes'),
    path('facturas/pagadas/', views.FacturasPagadasListView.as_view(), name='facturas_pagadas'),
    path('pago/registrar/<int:invoice_id>/', views.CobroFacturaCreateView.as_view(), name='registrar_pago'),
    path('pago/editar/<int:pk>/', views.CobroFacturaUpdateView.as_view(), name='editar_pago'),
    path('pago/eliminar/<int:pk>/', views.CobroFacturaDeleteView.as_view(), name='eliminar_pago'),
    path('historial/', views.HistorialPagosListView.as_view(), name='historial_pagos'),
    path('historial/factura/<int:invoice_id>/', views.HistorialPagosListView.as_view(), name='historial_factura'),

    # PAGOS DE COMPRAS (CUENTAS POR PAGAR)
    path('compras/', views.PagosComprasHomeView.as_view(), name='pagos_compras_home'),
    path('compras/pendientes/', views.ComprasPendientesListView.as_view(), name='compras_pendientes'),
    path('compras/pagadas/', views.ComprasPagadasListView.as_view(), name='compras_pagadas'),
    path('compras/pago/registrar/<int:purchase_id>/', views.PagoCompraCreateView.as_view(), name='registrar_pago_compra'),
    path('compras/pago/editar/<int:pk>/', views.PagoCompraUpdateView.as_view(), name='editar_pago_compra'),
    path('compras/pago/eliminar/<int:pk>/', views.PagoCompraDeleteView.as_view(), name='eliminar_pago_compra'),
    path('compras/historial/', views.HistorialPagosComprasListView.as_view(), name='historial_pagos_compras'),
    path('compras/historial/compra/<int:purchase_id>/', views.HistorialPagosComprasListView.as_view(), name='historial_pago_compra'),
]
