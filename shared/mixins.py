from django.contrib import messages
from django.shortcuts import redirect


class StaffRequiredMixin:
    """
    Mixin que verifica si el usuario es miembro del staff.
    Si no es staff, redirige con mensaje de error.
    
    Uso:
        class BrandDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
            ...
    
    ¿POR QUÉ?
    Porque solo el personal autorizado (staff) debe poder
    eliminar registros. Un usuario normal puede ver y crear,
    pero no borrar información importante del sistema.
    
    ¿CÓMO FUNCIONA?
    1. El usuario intenta acceder a una vista protegida
    2. dispatch() se ejecuta ANTES que la vista
    3. Si user.is_staff es False → redirige con mensaje de error
    4. Si user.is_staff es True → ejecuta la vista normalmente
    """

    # URL a donde redirigir si no es staff
    # Se puede sobreescribir en cada vista
    staff_redirect_url = '/'
    staff_error_message = 'You do not have permission to perform this action. Staff access required.'

    def dispatch(self, request, *args, **kwargs):
        """
        dispatch() es el primer método que se ejecuta en una CBV.
        Interceptamos aquí para verificar permisos ANTES de
        procesar la petición (GET o POST).
        """
        # Verificar si el usuario es staff
        if not request.user.is_staff:
            # Mostrar mensaje de error al usuario
            messages.error(request, self.staff_error_message)
            # Redirigir a la URL configurada
            return redirect(self.staff_redirect_url)

        # Si es staff, continuar con el flujo normal de la vista
        return super().dispatch(request, *args, **kwargs)

class GroupRequiredMixin:
    """
    Mixin que verifica si el usuario pertenece a alguno
    de los roles (grupos) indicados en group_required.

    Uso:
        class GroupListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
            group_required = ['Administrador']
    """
    group_required = []        # Lista de roles permitidos
    group_redirect_url = '/'   # A dónde redirigir si no tiene el rol
    group_error_message = 'You do not have permission to access this option.'

    def dispatch(self, request, *args, **kwargs):
        # 1. Si no inició sesión -> al login
        if not request.user.is_authenticated:
            return redirect('login')
        # 2. El superusuario siempre pasa
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        # 3. ¿Pertenece a alguno de los roles permitidos?
        if request.user.groups.filter(name__in=self.group_required).exists():
            return super().dispatch(request, *args, **kwargs)
        # 4. No tiene el rol -> mensaje de error y redirección
        messages.error(request, self.group_error_message)
        return redirect(self.group_redirect_url)


from django.contrib.auth.mixins import PermissionRequiredMixin as DjangoPermissionRequiredMixin

class PermissionRequiredMixin(DjangoPermissionRequiredMixin):
    """
    Mixin que verifica si el usuario tiene los permisos requeridos.
    Si no los tiene, redirige al Home con un mensaje de error.
    El superusuario siempre pasa.
    """
    permission_redirect_url = '/'
    permission_error_message = 'No tienes permiso para acceder a esta opción.'

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('login')
        messages.error(self.request, self.permission_error_message)
        return redirect(self.permission_redirect_url)

