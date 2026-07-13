from django.urls import path
from . import views
app_name = 'billing'
urlpatterns = [
    path('', views.home, name='home'),
    # Auth 
    path('signup/', views.SignUpView.as_view(), name='signup'),
    # Brand (FBV)
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/create/', views.brand_create, name='brand_create'),
    path('brands/report/pdf/', views.brand_report_pdf, name='brand_report_pdf'),
    path('brands/report/excel/', views.brand_report_excel, name='brand_report_excel'),
    path('brands/<int:pk>/edit/', views.brand_update, name='brand_update'),
    path('brands/<int:pk>/delete/', views.brand_delete, name='brand_delete'),
    # ProductGroup
    path('groups/', views.ProductGroupListView.as_view(), name='productgroup_list'),
    path('groups/create/', views.ProductGroupCreateView.as_view(), name='productgroup_create'),
    path('groups/report/pdf/', views.productgroup_report_pdf, name='productgroup_report_pdf'),
    path('groups/report/excel/', views.productgroup_report_excel, name='productgroup_report_excel'),
    path('groups/<int:pk>/edit/', views.ProductGroupUpdateView.as_view(), name='productgroup_update'),
    path('groups/<int:pk>/delete/', views.ProductGroupDeleteView.as_view(), name='productgroup_delete'),
    # Supplier
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/report/pdf/', views.supplier_report_pdf, name='supplier_report_pdf'),
    path('suppliers/report/excel/', views.supplier_report_excel, name='supplier_report_excel'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),
    # Product
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/report/pdf/', views.product_report_pdf, name='product_report_pdf'),
    path('products/report/excel/', views.product_report_excel, name='product_report_excel'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    # Customer
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/report/pdf/', views.customer_report_pdf, name='customer_report_pdf'),
    path('customers/report/excel/', views.customer_report_excel, name='customer_report_excel'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer_delete'),
    # Invoice
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/create/', views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/report/pdf/', views.invoice_report_pdf, name='invoice_report_pdf'),
    path('invoices/report/excel/', views.invoice_report_excel, name='invoice_report_excel'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoices/<int:pk>/paypal/checkout/', views.invoice_paypal_checkout, name='invoice_paypal_checkout'),
    path('invoices/<int:pk>/paypal/capture/', views.invoice_paypal_capture, name='invoice_paypal_capture'),
    path('invoices/<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice_delete'),
]
