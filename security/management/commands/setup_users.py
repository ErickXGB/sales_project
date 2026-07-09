from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

class Command(BaseCommand):
    help = 'Crea los usuarios de prueba (administrador, gerente, comprador, vendedor) y los asigna a sus grupos correspondientes'

    def handle(self, *args, **kwargs):
        users_config = [
            ('administrador', 'administrador@test.com', 'pass1234', 'Administrador'),
            ('gerente', 'gerente@test.com', 'pass1234', 'Gerente'),
            ('comprador', 'comprador@test.com', 'pass1234', 'Compras'),
            ('vendedor', 'vendedor@test.com', 'pass1234', 'Ventas'),
        ]

        for username, email, password, group_name in users_config:
            # Eliminar usuario si ya existe para evitar colisiones al ejecutar de nuevo
            User.objects.filter(username=username).delete()

            # Crear usuario
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=username.capitalize(),
                last_name='Prueba'
            )

            # Buscar grupo y asignar
            try:
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
                self.stdout.write(self.style.SUCCESS(
                    f'Usuario "{username}" creado con contraseña "{password}" y asignado al grupo "{group_name}".'
                ))
            except Group.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'Error: El grupo "{group_name}" no existe. Ejecuta primero setup_roles.'
                ))
