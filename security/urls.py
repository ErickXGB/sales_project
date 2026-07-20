from django.urls import path
from . import views

app_name = 'security'

urlpatterns = [
    # Panel Principal de Seguridad
    path('', views.SecurityHomeView.as_view(), name='security_home'),

    # Autenticación
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.SecurityLoginView.as_view(), name='login'),
    path('logout/', views.SecurityLogoutView.as_view(), name='logout'),

    # Usuarios
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.AdminUserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('users/<int:pk>/permissions/', views.UserPermissionsView.as_view(), name='user_permissions'),
    path('users/update-permission/', views.update_user_permission, name='update_user_permission'),

    # Roles (Group)
    path('roles/', views.GroupListView.as_view(), name='group_list'),
    path('roles/create/', views.GroupCreateView.as_view(), name='group_create'),
    path('roles/update-permission/', views.update_group_permission, name='update_permission'),
    path('roles/export-permissions/', views.export_permissions_json, name='export_permissions'),
    path('roles/reset-permissions/', views.reset_permissions, name='reset_permissions'),
    path('roles/<int:pk>/edit/', views.GroupUpdateView.as_view(), name='group_update'),
    path('roles/<int:pk>/delete/', views.GroupDeleteView.as_view(), name='group_delete'),

    # Permisos (Permission)
    path('permissions/', views.PermissionListView.as_view(), name='permission_list'),
    path('permissions/create/', views.PermissionCreateView.as_view(), name='permission_create'),
    path('permissions/<int:pk>/edit/', views.PermissionUpdateView.as_view(), name='permission_update'),
    path('permissions/<int:pk>/delete/', views.PermissionDeleteView.as_view(), name='permission_delete'),
]
