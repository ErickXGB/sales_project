# Sistema de Ventas y Compras con Roles, Pasarela PayPal y Notificación WhatsApp

Este proyecto es una plataforma web desarrollada en **Django** para la gestión comercial y financiera de una empresa. El sistema incluye módulos para el control de inventario, ventas, facturación, cuentas por cobrar (cobro de facturas), cuentas por pagar (pagos de compras), notificaciones simuladas por WhatsApp, pasarela de pagos con **PayPal Sandbox**, y un robusto control de accesos basado en roles y permisos de Django.

---

## 🛠️ Tecnologías Utilizadas
*   **Backend**: Python (Django Framework)
*   **Base de Datos**: SQLite (entorno local)
*   **Frontend**: HTML5, CSS3, Javascript, Bootstrap 5, Bootstrap Icons
*   **Integraciones**: SDK de PayPal Smart Buttons (JavaScript & Rest API)

---

## 📁 Estructura del Proyecto

El código fuente del sistema está organizado en las siguientes aplicaciones y directorios principales:

*   **`config/`**: Configuración global de la aplicación (configuración del entorno, base de datos, urls principales, ajustes de templates y cargadores de variables de entorno con `python-decouple`).
*   **`billing/`**: Aplicación núcleo que administra:
    *   Marcas (`Brand`), Grupos/Categorías (`ProductGroup`), Clientes (`Customer`), Productos (`Product`) e Historial de Facturación (`Invoice`, `InvoiceDetail`).
    *   Controladores de inicio personalizado por roles (`home`) y lógica de checkout de PayPal.
*   **`purchasing/`**: Aplicación encargada del aprovisionamiento:
    *   Gestión de proveedores (`Supplier`), registro de facturas de compras (`Purchase`) e insumos (`PurchaseDetail`).
*   **`pagos/`**: Módulo financiero (Cuentas por Cobrar y Pagar):
    *   Abonos de clientes sobre facturas a crédito (`CobroFactura`).
    *   Abonos de la empresa sobre compras a crédito (`PagoCompra`).
    *   Vistas de Dashboards financieros e historiales de abonos.
*   **`security/`**: Gestión de accesos y seguridad:
    *   Decoradores y Mixins personalizados para la protección de vistas (`PermissionRequiredMixin`, `LoginRequiredMixin`).
    *   Comando administrativo `setup_roles` para inicializar grupos y permisos.
*   **`templates/`**: Directorio de plantillas globales (diseños de base, login, restauración de claves y cambio de contraseña).

---

## ⚙️ Modificaciones Realizadas y Cómo se Implementaron

### 1. Sistema de Seguridad y Roles
*   Se configuró un decorador y un comando personalizado (`python manage.py setup_roles`) que automatiza la creación y actualización de los roles del sistema:
    *   **Administrador**: Acceso ilimitado.
    *   **Gerente**: Acceso exclusivo de consulta (Lectura) a todo el sistema, sin permisos de modificación o eliminación.
    *   **Ventas**: Permiso de gestión completa para clientes, facturación y cobro de abonos. No puede ver el módulo de compras.
    *   **Compras**: Permiso de gestión completa para proveedores, compras y pagos de compras. No puede ver el módulo de ventas.
*   Se protegieron todas las vistas del sistema heredando de `LoginRequiredMixin` y `PermissionRequiredMixin`. Si un usuario intenta acceder a una ruta no autorizada, el sistema responde con una pantalla de **Acceso Denegado (403 Forbidden)**.

### 2. Panel de Inicio (Home) Inteligente
*   La vista `home` evalúa dinámicamente el rol del usuario conectado y renderiza un dashboard personalizado:
    *   **Administrador**: Acceso rápido a auditorías, seguridad, y alertas de productos con bajo stock.
    *   **Gerente**: Tarjetas de KPIs agregados con 2 decimales (Ventas Totales, Compras Totales, Cuentas por Cobrar, Cuentas por Pagar) y comparativas rápidas.
    *   **Ventas**: KPIs de facturación y lista de clientes con saldos vencidos.
    *   **Compras**: KPIs de stock, compras pendientes de pago y productos con bajo stock.

### 3. Integración de Pasarela de Pagos PayPal
*   Se agregó la opción de pago **"Contado (PayPal)"** en las facturas de venta. Al crearse, la factura queda en estado `PENDIENTE` y se redirige al cliente a una pasarela de pago segura (`/paypal/checkout/`).
*   En la interfaz, los Smart Buttons oficiales de PayPal procesan el pago seguro y, mediante una llamada API de backend segura (`/paypal/capture/`), el servidor de Django confirma y captura la transacción, rebajando el saldo de la factura a `$0.00` y guardando el abono en el modelo `CobroFactura` atómicamente.

### 4. Notificaciones por WhatsApp
*   Tanto en facturas de venta como de compra, se implementaron propiedades dinámicas (`whatsapp_phone` y `whatsapp_message`) para formatear el número celular (soportando números con prefijos internacionales `+` y nacionales sin `0`) y generar plantillas automáticas con el resumen de la compra o cobro.
*   En el listado y detalle de documentos, se incluyeron botones de acción directa con el logo de WhatsApp que abren una pestaña de redirección automática a la API de WhatsApp Web con el mensaje pre-llenado.

### 5. Control de Navegación del Perfil de Usuario
*   El nombre de usuario en la barra de navegación se transformó en un menú desplegable (dropdown).
*   Se crearon e integraron vistas estilizadas para el **Cambio de Contraseña** de los usuarios directamente desde el sistema, con redirección y alertas de seguridad.

---

## 🚀 Instrucciones de Configuración Inicial

1.  **Configurar Variables de Entorno**:
    *   Crea o edita el archivo `.env` en la raíz del proyecto y añade tu Client ID de PayPal Sandbox:
        ```env
        PAYPAL_CLIENT_ID=tu_client_id_largo_de_paypal
        ```
2.  **Ejecutar Migraciones de Base de Datos**:
    ```bash
    python manage.py migrate
    ```
3.  **Generar Roles y Permisos**:
    ```bash
    python manage.py setup_roles
    ```
4.  **Iniciar Servidor de Desarrollo**:
    ```bash
    python manage.py runserver
    ```