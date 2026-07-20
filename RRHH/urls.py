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
    # Exportaciones
    path('sobretiempos/exportar/pdf/', views.export_sobretiempo_list_pdf, name='sobretiempo_list_pdf'),
    path('sobretiempos/exportar/excel/', views.export_sobretiempo_list_excel, name='sobretiempo_list_excel'),
    path('sobretiempos/<int:pk>/exportar/pdf/', views.export_sobretiempo_detail_pdf, name='sobretiempo_detail_pdf'),
    path('sobretiempos/<int:pk>/exportar/excel/', views.export_sobretiempo_detail_excel, name='sobretiempo_detail_excel'),
]
