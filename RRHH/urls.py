from django.urls import path
from . import views

app_name = 'rrhh'

urlpatterns = [
    path('sobretiempos/', views.SobretiempoListView.as_view(), name='sobretiempo_list'),
    path('sobretiempos/nuevo/', views.SobretiempoCreateView.as_view(), name='sobretiempo_create'),
    path('sobretiempos/<int:pk>/', views.SobretiempoDetailView.as_view(), name='sobretiempo_detail'),
    path('sobretiempos/<int:pk>/editar/', views.SobretiempoUpdateView.as_view(), name='sobretiempo_update'),
    path('sobretiempos/<int:pk>/eliminar/', views.SobretiempoDeleteView.as_view(), name='sobretiempo_delete'),
    path('sobretiempos/resumen/', views.SobretiempoResumenView.as_view(), name='sobretiempo_resumen'),
    # Exportaciones Sobretiempo
    path('sobretiempos/exportar/pdf/', views.export_sobretiempo_list_pdf, name='sobretiempo_list_pdf'),
    path('sobretiempos/exportar/excel/', views.export_sobretiempo_list_excel, name='sobretiempo_list_excel'),
    path('sobretiempos/<int:pk>/exportar/pdf/', views.export_sobretiempo_detail_pdf, name='sobretiempo_detail_pdf'),
    path('sobretiempos/<int:pk>/exportar/excel/', views.export_sobretiempo_detail_excel, name='sobretiempo_detail_excel'),

    # Préstamos
    path('prestamos/', views.PrestamoListView.as_view(), name='prestamo_list'),
    path('prestamos/nuevo/', views.PrestamoCreateView.as_view(), name='prestamo_create'),
    path('prestamos/<int:pk>/', views.PrestamoDetailView.as_view(), name='prestamo_detail'),
    path('prestamos/<int:pk>/editar/', views.PrestamoUpdateView.as_view(), name='prestamo_update'),
    path('prestamos/<int:pk>/eliminar/', views.PrestamoDeleteView.as_view(), name='prestamo_delete'),
    path('prestamos/resumen/', views.PrestamoResumenView.as_view(), name='prestamo_resumen'),
    path('prestamos/cuota/<int:cuota_id>/pagar/', views.pagar_cuota_prestamo, name='pagar_cuota'),
    # Exportaciones Préstamos
    path('prestamos/exportar/pdf/', views.export_prestamo_list_pdf, name='prestamo_list_pdf'),
    path('prestamos/exportar/excel/', views.export_prestamo_list_excel, name='prestamo_list_excel'),
    path('prestamos/<int:pk>/exportar/pdf/', views.export_prestamo_detail_pdf, name='prestamo_detail_pdf'),
]

