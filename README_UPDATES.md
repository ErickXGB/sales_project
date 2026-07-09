# Actualizaciones del Sistema – Control de Acceso y Funcionalidades PDF/Email

Este documento resume los cambios, configuraciones y nuevas características implementadas en el sistema de ventas hoy para robustecer la seguridad y automatizar procesos de negocio.

---

## 🔒 1. Seguridad y Autenticación

### Configuración de Servidor de Correo (SMTP)
*   Se configuró el entorno seguro para el envío de correos electrónicos a través del backend SMTP de Gmail en `config/settings.py`.
*   Las credenciales sensibles (`EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD`) fueron extraídas de forma segura al archivo `.env` mediante el uso de la biblioteca `python-decouple`, protegiendo así la información confidencial.

### Desactivación de Vistas Públicas de Registro
*   Para garantizar que únicamente los administradores gestionen las cuentas, se restringió el acceso público a las vistas de registro:
    *   `SignUpView` (Facturación) y `RegisterView` (Seguridad) ahora heredan de `UserPassesTestMixin` y requieren permisos de **Superusuario** (`is_superuser`) para ser accedidas. Si un usuario no autenticado intenta ingresar, es redirigido al panel de inicio de sesión.

---

## 👥 2. Roles, Usuarios y Permisos

### Grupos de Trabajo (Roles)
Se reestructuraron por completo los grupos de Django para reflejar la estructura solicitada:
1.  **Administrador**: Acceso completo a todo el sistema.
2.  **Gerente**: Consulta total de información (Marcas, Grupos, Proveedores, Productos, Clientes, Facturas, Compras). Sin permisos de escritura/modificación/eliminación.
3.  **Compras**: Administración y gestión de Proveedores, Compras y sus Detalles. Lectura del catálogo de productos.
4.  **Ventas**: Administración y gestión de Clientes, Facturas y sus Detalles. Lectura del catálogo de productos.

### Comandos de Inicialización
*   `python manage.py setup_roles`: Inicializa los cuatro roles mencionados y asocia sus correspondientes permisos nativos de Django. Elimina roles anteriores descatalogados (`Vendedor`, `Analista de Compras`).
*   `python manage.py setup_users`: Crea de forma limpia los cuatro usuarios de prueba (`administrador`, `gerente`, `comprador`, `vendedor`) con la contraseña estándar `pass1234` y los vincula a sus grupos correspondientes.

### Control de Acceso por Permisos Nativos
*   Se migraron todas las vistas de validación por nombres de grupo (`group_required`) al sistema de **Permisos Nativos de Django** (`view_`, `add_`, `change_`, `delete_`).
*   Se diseñaron el mixin `PermissionRequiredMixin` (`shared/mixins.py`) y el decorador `permission_required` (`shared/decorators.py`) para interceptar accesos no autorizados y redirigir al Home con un mensaje de alerta amigable.

---

## 📄 3. Impresión y Envío Automatizado

### Descarga e Impresión Individual de PDFs
Se habilitó la opción para generar e imprimir documentos individuales en PDF estilizados utilizando `ReportLab`:
*   **Facturas de Venta:** Habilitado el botón "Imprimir / PDF" en el listado y detalle de facturas (`invoices/<int:pk>/pdf/`).
*   **Adquisiciones (Compras):** Habilitado el botón "Imprimir / PDF" en el listado y detalle de compras (`purchases/<int:pk>/pdf/`).

### Envío de Facturas por Correo Electrónico
*   Al crear una factura de venta, si el cliente seleccionado dispone de un correo electrónico registrado, el sistema genera automáticamente el PDF de la factura, lo adjunta y lo envía al correo del cliente.
*   En caso de existir algún problema con el servidor SMTP, el sistema atrapa el error y muestra un mensaje de advertencia al vendedor, permitiendo que la factura se guarde correctamente en la base de datos sin interrumpir el proceso de facturación.

---

## 🧭 4. Experiencia de Usuario (Menú de Navegación)
*   Se actualizó la barra de navegación del sitio en `billing/templates/billing/base.html` para habilitar de forma transparente el acceso al menú de consulta completo (Marcas, Categorías/Grupos, Proveedores, Productos, Compras, Clientes, Facturas) al grupo **Gerente**, además de los grupos específicos autorizados.
