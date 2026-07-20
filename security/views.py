from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.views import LoginView, LogoutView
from django.core.mail import send_mail
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, TemplateView

from shared.mixins import GroupRequiredMixin
from .forms import UserRegisterForm, UserUpdateForm, GroupForm, PermissionForm

# === MIXIN BASE: SOLO ADMINISTRADOR ===
class AdminOnlyMixin(LoginRequiredMixin, GroupRequiredMixin):
    """Combina login + rol Administrador (el superusuario siempre pasa)."""
    group_required = ['Administrador']
    group_redirect_url = '/'


# === PANEL DE INICIO DE SEGURIDAD ===
class SecurityHomeView(AdminOnlyMixin, TemplateView):
    template_name = 'security/security_home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_users'] = User.objects.count()
        context['total_groups'] = Group.objects.count()
        context['total_permissions'] = Permission.objects.count()
        context['recent_users'] = User.objects.order_by('-date_joined')[:5]
        context['recent_logins'] = User.objects.filter(last_login__isnull=False).order_by('-last_login')[:5]
        return context


# === AUTENTICACIÓN (CBV) ===
class RegisterView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Registro público con selección de rol (desactivado para público general)."""
    form_class = UserRegisterForm
    template_name = 'security/register.html'
    success_url = reverse_lazy('billing:home')

    def test_func(self):
        # Desactivado para el público general; solo superusuarios pueden acceder.
        return self.request.user.is_superuser

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)   # inicia sesión automáticamente
        return response

class SecurityLoginView(LoginView):
    """Login con CBV. Reutiliza el template de la PARTE 9."""
    template_name = 'registration/login.html'

    def form_valid(self, form):
        remember_me = self.request.POST.get('remember_me')
        if remember_me:
            # La sesión durará 2 semanas (1209600 segundos)
            self.request.session.set_expiry(1209600)
        else:
            # La sesión expira al cerrar el navegador
            self.request.session.set_expiry(0)
        return super().form_valid(form)

class SecurityLogoutView(LogoutView):
    """Logout con CBV. Redirige según LOGOUT_REDIRECT_URL."""
    pass

# === USUARIOS (solo Administrador) ===
class UserListView(AdminOnlyMixin, ListView):
    model = User
    template_name = 'security/user_list.html'
    context_object_name = 'items'
    paginate_by = 10

class AdminUserCreateView(AdminOnlyMixin, CreateView):
    """El Administrador crea un usuario con contraseña manual y envía credenciales por correo."""
    model = User
    form_class = UserRegisterForm
    template_name = 'security/user_create.html'
    success_url = reverse_lazy('security:user_list')

    def form_valid(self, form):
        # Capturar la contraseña en texto plano ANTES de que super() la hashee
        plain_password = form.cleaned_data['password1']

        # super() guarda el usuario correctamente y setea self.object
        response = super().form_valid(form)
        user = self.object

        # Enviar correo con las credenciales ingresadas
        send_mail(
            subject='Bienvenido/a – Tus credenciales de acceso',
            message=(
                f'Hola {user.first_name or user.username},\n\n'
                f'Tu cuenta ha sido creada exitosamente.\n\n'
                f'Usuario: {user.username}\n'
                f'Contraseña: {plain_password}\n\n'
                f'Por seguridad, cambia tu contraseña después de iniciar sesión.\n\n'
                f'Saludos,\nEquipo de administración'
            ),
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )

        messages.success(
            self.request,
            f'Usuario "{user.username}" creado y correo enviado a {user.email}.'
        )
        return response


class UserUpdateView(AdminOnlyMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'security/user_form.html'
    success_url = reverse_lazy('security:user_list')

class UserDeleteView(AdminOnlyMixin, DeleteView):
    model = User
    template_name = 'security/confirm_delete.html'
    success_url = reverse_lazy('security:user_list')

# === ROLES / GROUP (solo Administrador) ===
class GroupListView(AdminOnlyMixin, ListView):
    model = Group
    template_name = 'security/group_list.html'
    context_object_name = 'items'
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Lista de modelos y sus acciones para la matriz
        models_config = [
            {'label': 'Marca', 'codename_base': 'brand'},
            {'label': 'Categoría', 'codename_base': 'productgroup'},
            {'label': 'Proveedor', 'codename_base': 'supplier'},
            {'label': 'Producto', 'codename_base': 'product'},
            {'label': 'Cliente', 'codename_base': 'customer'},
            {'label': 'Factura', 'codename_base': 'invoice'},
            {'label': 'Compra', 'codename_base': 'purchase'},
            {'label': 'Cobro Factura', 'codename_base': 'cobrofactura'},
            {'label': 'Pago Compra', 'codename_base': 'pagocompra'},
            {'label': 'Usuario', 'codename_base': 'user'},
            {'label': 'Sobretiempo', 'codename_base': 'sobretiempo'},
        ]
        
        actions = [
            {'suffix': 'view', 'label': 'Leer'},
            {'suffix': 'detail', 'label': 'Detalle'},
            {'suffix': 'add', 'label': 'Crear'},
            {'suffix': 'change', 'label': 'Editar'},
            {'suffix': 'delete', 'label': 'Eliminar'},
            {'suffix': 'download_pdf', 'label': 'PDF'},
            {'suffix': 'download_excel', 'label': 'Excel'},
            {'suffix': 'whatsapp', 'label': 'WhatsApp'},
        ]
        
        # Generar lista plana de columnas para facilitar el rendering
        columns = []
        for mc in models_config:
            for act in actions:
                if act['suffix'] == 'download_pdf':
                    codename = f"download_{mc['codename_base']}_pdf"
                elif act['suffix'] == 'download_excel':
                    codename = f"download_{mc['codename_base']}_excel"
                else:
                    codename = f"{act['suffix']}_{mc['codename_base']}"
                columns.append({
                    'codename': codename,
                    'label': f"{act['label']} {mc['label']}",
                    'model_label': mc['label'],
                    'action_label': act['label']
                })
                
        context['models_config'] = models_config
        context['actions'] = actions
        context['matrix_columns'] = columns
        
        from django.contrib.auth.models import Permission
        context['db_permissions'] = set(Permission.objects.values_list('codename', flat=True))
        
        # Preparar datos de filas
        groups_data = []
        for g in context['object_list'].prefetch_related('permissions'):
            g_perms = set(p.codename for p in g.permissions.all())
            groups_data.append({
                'group': g,
                'perms': g_perms,
                'total_count': len(g_perms),
            })
            
        context['groups_data'] = groups_data
        context['total_permissions_count'] = len(columns)
        return context

class GroupCreateView(AdminOnlyMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = 'security/group_form.html'
    success_url = reverse_lazy('security:group_list')

class GroupUpdateView(AdminOnlyMixin, UpdateView):
    model = Group
    form_class = GroupForm
    template_name = 'security/group_form.html'
    success_url = reverse_lazy('security:group_list')

class GroupDeleteView(AdminOnlyMixin, DeleteView):
    model = Group
    template_name = 'security/confirm_delete.html'
    success_url = reverse_lazy('security:group_list')

# === PERMISOS / PERMISSION (solo Administrador) ===
class PermissionListView(AdminOnlyMixin, ListView):
    model = Permission
    template_name = 'security/permission_list.html'
    context_object_name = 'items'
    queryset = Permission.objects.select_related('content_type')
    paginate_by = 10

class PermissionCreateView(AdminOnlyMixin, CreateView):
    model = Permission
    form_class = PermissionForm
    template_name = 'security/permission_form.html'
    success_url = reverse_lazy('security:permission_list')

class PermissionUpdateView(AdminOnlyMixin, UpdateView):
    model = Permission
    form_class = PermissionForm
    template_name = 'security/permission_form.html'
    success_url = reverse_lazy('security:permission_list')

class PermissionDeleteView(AdminOnlyMixin, DeleteView):
    model = Permission
    template_name = 'security/confirm_delete.html'
    success_url = reverse_lazy('security:permission_list')


# === ACCIONES AJAX Y EXPORTACIÓN DE LA MATRIZ ===
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import user_passes_test
from django.core.management import call_command
import json

def is_admin_or_superuser(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Administrador').exists())

@user_passes_test(is_admin_or_superuser, login_url='/')
@require_POST
def update_group_permission(request):
    try:
        data = json.loads(request.body)
        group_id = data.get('group_id')
        codename = data.get('codename')
        state = data.get('state')
        
        group = Group.objects.get(pk=group_id)
        permission = Permission.objects.get(codename=codename)
        
        if state:
            group.permissions.add(permission)
        else:
            group.permissions.remove(permission)
            
        return JsonResponse({'success': True, 'count': group.permissions.count()})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@user_passes_test(is_admin_or_superuser, login_url='/')
def export_permissions_json(request):
    try:
        data = {}
        groups = Group.objects.all().prefetch_related('permissions')
        for g in groups:
            data[g.name] = [p.codename for p in g.permissions.all()]
            
        from django.http import HttpResponse
        response = HttpResponse(json.dumps(data, indent=4), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="roles_permisos.json"'
        return response
    except Exception as e:
        messages.error(request, f"Error al exportar JSON: {str(e)}")
        return redirect('security:group_list')

@user_passes_test(is_admin_or_superuser, login_url='/')
@require_POST
def reset_permissions(request):
    try:
        call_command('setup_roles')
        return JsonResponse({'success': True, 'message': 'Roles y permisos restablecidos al estado predeterminado con éxito.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


class UserPermissionsView(AdminOnlyMixin, TemplateView):
    template_name = 'security/user_permissions.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.shortcuts import get_object_or_404
        user = get_object_or_404(User, pk=self.kwargs.get('pk'))
        
        # User direct permissions
        direct_perms = set(p.codename for p in user.user_permissions.all())
        
        # User inherited permissions from their groups
        inherited_perms = set()
        for group in user.groups.all():
            inherited_perms.update(p.codename for p in group.permissions.all())
            
        models_config = [
            {'label': 'Marca', 'codename_base': 'brand'},
            {'label': 'Categoría', 'codename_base': 'productgroup'},
            {'label': 'Proveedor', 'codename_base': 'supplier'},
            {'label': 'Producto', 'codename_base': 'product'},
            {'label': 'Cliente', 'codename_base': 'customer'},
            {'label': 'Factura', 'codename_base': 'invoice'},
            {'label': 'Compra', 'codename_base': 'purchase'},
            {'label': 'Cobro Factura', 'codename_base': 'cobrofactura'},
            {'label': 'Pago Compra', 'codename_base': 'pagocompra'},
            {'label': 'Usuario', 'codename_base': 'user'},
            {'label': 'Sobretiempo', 'codename_base': 'sobretiempo'},
        ]
        
        actions = [
            {'suffix': 'view', 'label': 'Leer'},
            {'suffix': 'detail', 'label': 'Detalle'},
            {'suffix': 'add', 'label': 'Crear'},
            {'suffix': 'change', 'label': 'Editar'},
            {'suffix': 'delete', 'label': 'Eliminar'},
            {'suffix': 'download_pdf', 'label': 'PDF'},
            {'suffix': 'download_excel', 'label': 'Excel'},
            {'suffix': 'whatsapp', 'label': 'WhatsApp'},
        ]
        
        context['target_user'] = user
        context['direct_perms'] = direct_perms
        context['inherited_perms'] = inherited_perms
        context['models_config'] = models_config
        context['actions'] = actions
        context['db_permissions'] = set(Permission.objects.values_list('codename', flat=True))
        
        return context


@user_passes_test(is_admin_or_superuser, login_url='/')
@require_POST
def update_user_permission(request):
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        codename = data.get('codename')
        state = data.get('state')
        
        user = User.objects.get(pk=user_id)
        permission = Permission.objects.get(codename=codename)
        
        if state:
            user.user_permissions.add(permission)
        else:
            user.user_permissions.remove(permission)
            
        return JsonResponse({'success': True, 'count': user.user_permissions.count()})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

