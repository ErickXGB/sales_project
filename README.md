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
*   **`sri_microservice/`**: Microservicio autónomo desarrollado en **FastAPI** para la facturación electrónica en Ecuador:
    *   Generación de XML estructurado de facturas según el estándar del SRI.
    *   Firma criptográfica XAdES-BES en memoria mediante `signxml` y `cryptography` con soporte para certificados `.p12`.
    *   Envío SOAP y consulta de autorización mediante `zeep` con los Web Services del SRI (Recepcion y Autorizacion).

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

### 6. Facturación Electrónica SRI (Ecuador)
*   Se desarrolló un microservicio dedicado en `sri_microservice` con FastAPI.
*   **Firma e Integración:** Cuando se guarda una factura en Django, se hace una petición POST al microservicio. El microservicio valida, estructura el XML, firma el comprobante con la firma digital `.p12` cargada localmente o enviada en base64, y realiza el envío al Web Service del SRI.
*   **Visualización:** En el detalle de la factura se despliega la clave de acceso de 49 dígitos generada por el SRI, junto con el estado del SRI y un botón de copiado rápido al portapapeles.

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
4.  **Iniciar Servidor de Desarrollo (Django)**:
    ```bash
    python manage.py runserver
    ```

---

## 🚀 Instrucciones de Configuración y Ejecución del Microservicio SRI

El microservicio SRI corre de manera independiente en el puerto **8001**.

1.  **Configurar Variables de Entorno del Microservicio**:
    *   Crea o edita el archivo `sri_microservice/.env` con la configuración del certificado y el entorno de pruebas del SRI:
        ```env
        SRI_ENVIRONMENT=PRUEBAS
        SRI_CERT_PATH=certs/Firma.p12
        SRI_CERT_PASSWORD=Mamatequiero12
        SRI_VERIFY_SSL=True
        ```
2.  **Colocar Firma Electrónica**:
    *   Guarda tu firma digital autorizada por el SRI en formato `.p12` dentro de la carpeta `sri_microservice/certs/` (el archivo debe llamarse igual al configurado en `SRI_CERT_PATH`, ej. `Firma.p12`).
3.  **Instalar Dependencias del Microservicio**:
    ```bash
    pip install -r sri_microservice/requirements.txt
    ```
4.  **Ejecutar el Microservicio (FastAPI)**:
    ```bash
    cd sri_microservice
    python -m uvicorn main:app --port 8001 --reload
    ```
5.  **Verificación**:
    *   Asegúrate de que el microservicio esté activo en `http://127.0.0.1:8001/`. Al crear una factura en Django, se enviará y firmará automáticamente contra el SRI de Pruebas.


10. **Implementación de un Microservicio de Facturación Electrónica (SRI)**
    *   **Propósito:** Externalizar la complejidad del manejo de firmas digitales y las comunicaciones SOAP con el Servicio de Rentas Internas de Ecuador (SRI) fuera del núcleo de la aplicación Django, mejorando la seguridad, escalabilidad y mantenibilidad.
    *   **Arquitectura:** Se creó un microservicio autónomo en `sri_microservice/` desarrollado con **FastAPI**. Este servicio se ejecuta de manera independiente (`python -m uvicorn main:app --port 8001 --reload`) y expone una API REST segura.
    *   **Integración con Django:** La aplicación principal (Django) se comunica con este microservicio mediante peticiones HTTP POST cuando un usuario crea una factura. Esta comunicación se realiza utilizando el `requests` de Python, simulando un patrón de cliente-servidor donde Django delega la tarea de facturación electrónica al microservicio especializado.
    *   **Características Clave:**
        *   **Firma Digital Segura:** El microservicio maneja de forma segura el certificado `.p12` del contribuyente. Utiliza la librería `signxml` para firmar los comprobantes XML en memoria, aplicando la firma criptográfica XAdES-BES que exige el SRI.
        *   **Envío al SRI:** Una vez firmado, el XML es enviado mediante el protocolo SOAP a los Web Services oficiales del SRI (Recepcion y Autorizacion). La librería `zeep` se encarga de la comunicación SOAP y el manejo de errores.
        *   **Validación Automática:** El microservicio realiza validaciones sintácticas y estructurales del XML antes de enviarlo, asegurando que cumpla con el esquema establecido por el SRI.
        *   **Persistencia de Información:** Tras la respuesta del SRI, el microservicio devuelve la información relevante (Estado de Autorización, Clave de Acceso, Mensajes del SRI) a la aplicación Django, la cual se encarga de almacenar estos datos en la base de datos y mostrarlos al usuario en la interfaz.
        *   **Configuración Flexible:** Utiliza variables de entorno (`.env`) para gestionar parámetros sensibles como la ruta del certificado, contraseña y el ambiente de destino (PRUEBAS o PRODUCCION), facilitando su despliegue en diferentes entornos sin modificar el código.
    *   **Beneficios:**
        *   **Seguridad Mejorada:** Mantiene las claves privadas y la lógica de firma fuera del servidor de aplicaciones web principal (Django), reduciendo la superficie de ataque.
        *   **Aislamiento de Errores:** Un fallo en la comunicación con el SRI o un error en la firma no bloquea la aplicación principal, ya que la responsabilidad está delegada.
        *   **Mantenibilidad:** Permite actualizar las dependencias de firma o las integraciones con el SRI sin necesidad de redeployar la aplicación Django, siempre que la interfaz de API se mantenga estable.
        *   **Escalabilidad:** Facilita el escalado horizontal del servicio de facturación de forma independiente al resto de la aplicación.

        Sobretiempo sueldo mensual del empleado dividido para 240, y luego este valor lo voy a multiplicar por las horas trabajadas en sobretiempo

        dos registros, factor dos, extraordinaria y factor 1.5, ordinaria 
        empleado, varios empleados y sueldo. fecha de sobretiempo y detalle (tipo sobre tiempo)  ElFACTOR SE MULTIPLICA POR EL TIPO DE SOBRETIEMPO

sobretiempo = sueldo/240*horas*factortiposobretiempo