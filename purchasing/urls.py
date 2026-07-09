from django.urls import path
from . import views

app_name = 'purchasing'

urlpatterns = [
    path('', views.purchase_list, name='purchase_list'),
    path('create/', views.purchase_create, name='purchase_create'),
    path('report/', views.purchase_report, name='purchase_report'),
    path('report/pdf/', views.purchase_report_pdf, name='purchase_report_pdf'),
    path('report/excel/', views.purchase_report_excel, name='purchase_report_excel'),
    path('<int:pk>/', views.purchase_detail, name='purchase_detail'),
    path('<int:pk>/pdf/', views.purchase_pdf, name='purchase_pdf'),
    path('<int:pk>/delete/', views.purchase_delete, name='purchase_delete'),
]
