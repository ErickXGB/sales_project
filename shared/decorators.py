import logging
from functools import wraps
from django.utils import timezone

# Configurar logger para auditoría
# Los mensajes se guardan en la consola y pueden redirigirse a archivo
logger = logging.getLogger('audit')


def audit_action(action_name):
    """
    Decorador que registra las acciones del usuario para auditoría.
    
    Parámetros:
        action_name (str): Nombre de la acción a registrar.
                          Ejemplo: "CREATE_BRAND", "DELETE_PRODUCT"
    
    Uso:
        @login_required
        @audit_action("CREATE_BRAND")
        def brand_create(request):
            ...
    
    ¿POR QUÉ?
    Para tener un registro de quién hizo qué en el sistema.
    Si un producto es eliminado, puedes rastrear quién lo hizo.
    
    ¿CÓMO FUNCIONA?
    1. El usuario llama a la vista (ej: brand_create)
    2. El decorador intercepta ANTES de ejecutar la vista
    3. Registra: usuario, acción, fecha/hora, método HTTP, IP
    4. Ejecuta la vista normalmente
    5. Si el método es POST (envío de formulario), registra también
       que la acción fue completada
    """

    def decorator(view_func):
        @wraps(view_func)  # Preserva el nombre y docstring de la vista original
        def wrapper(request, *args, **kwargs):

            # Obtener datos del usuario y la petición
            user = request.user.username if request.user.is_authenticated else 'Anonymous'
            ip = request.META.get('REMOTE_ADDR', 'unknown')  # IP del usuario
            method = request.method  # GET o POST
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            path = request.path  # URL que visitó

            # Registrar la acción en el log
            logger.info(
                f'[AUDIT] {timestamp} | User: {user} | '
                f'Action: {action_name} | Method: {method} | '
                f'Path: {path} | IP: {ip}'
            )

            # También imprimir en consola para desarrollo
            print(
                f'\n[AUDIT] {timestamp} | User: {user} | '
                f'Action: {action_name} | Method: {method} | '
                f'Path: {path} | IP: {ip}'
            )

            # Ejecutar la vista original normalmente
            response = view_func(request, *args, **kwargs)

            # Si fue POST, registrar que la acción se completó
            if method == 'POST':
                print(f'[AUDIT] {timestamp} | COMPLETED: {action_name} by {user}')

            return response

        return wrapper
    return decorator


def group_required(*group_names, redirect_url='/'):
    """
    Decorador para vistas basadas en funciones que verifica si el usuario
    pertenece a alguno de los grupos (roles) indicados.
    Si no, redirige con mensaje de error.
    El superusuario siempre pasa.
    """
    from django.contrib import messages
    from django.shortcuts import redirect

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            messages.error(request, 'No tienes permiso para acceder a esta opción.')
            return redirect(redirect_url)
        return wrapper
    return decorator


def permission_required(*perm_names, redirect_url='/'):
    """
    Decorador para vistas basadas en funciones que verifica si el usuario
    posee todos los permisos de Django indicados en perm_names.
    Si no, redirige al Home con un mensaje de error.
    El superusuario siempre pasa.
    """
    from django.contrib import messages
    from django.shortcuts import redirect

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.has_perms(perm_names):
                return view_func(request, *args, **kwargs)
            messages.error(request, 'No tienes permiso para acceder a esta opción.')
            return redirect(redirect_url)
        return wrapper
    return decorator
