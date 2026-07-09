from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.views import LoginView, LogoutView
from django.core.mail import send_mail
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from shared.mixins import GroupRequiredMixin
from .forms import UserRegisterForm, UserUpdateForm, GroupForm, PermissionForm

# === MIXIN BASE: SOLO ADMINISTRADOR ===
class AdminOnlyMixin(LoginRequiredMixin, GroupRequiredMixin):
    """Combina login + rol Administrador (el superusuario siempre pasa)."""
    group_required = ['Administrador']
    group_redirect_url = '/'

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
