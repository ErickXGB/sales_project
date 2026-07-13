# Plan de Ejecución: Módulo de Cobros de Facturas a Crédito

Este plan detalla el diseño técnico y la implementación del módulo de cuentas por cobrar (**cobros**) en la aplicación Django. Se creará/completará la aplicación `pagos` para gestionar los abonos realizados por los clientes sobre las facturas emitidas a crédito.

---

## User Review Required

> [!IMPORTANT]
> **Modificaciones en la aplicación existente `billing`:**
> Se extenderá el modelo `Invoice` para incluir los campos `numero`, `tipo_pago`, `saldo` y `estado`, permitiendo diferenciar facturas de contado y crédito, y rastrear los saldos.
> Se adaptará la lógica de creación de facturas (`InvoiceCreateView` en `billing/views.py`) para establecer el tipo de pago, saldo inicial y estado según las condiciones de pago del perfil del cliente.

> [!WARNING]
> **Migración de datos de facturas existentes:**
> Se ejecutará un script de migración de datos para inicializar los campos nuevos en las 15 facturas ya existentes en la base de datos, asignándoles número, tipo de pago, saldo y estado correspondientes.

---

## Proposed Changes

### Django Config

#### [MODIFY] [settings.py](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/config/settings.py)
- Agregar `'pagos'` a la lista `INSTALLED_APPS`.

#### [MODIFY] [urls.py](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/config/urls.py)
- Incluir las rutas de la aplicación `pagos` bajo el prefijo `cobros/` con namespace `pagos`:
  ```python
  path('cobros/', include('pagos.urls', namespace='pagos')),
  ```

---

### Billing App (Facturación Existente)

#### [MODIFY] [models.py](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/billing/models.py)
- Agregar al modelo `Invoice` los siguientes campos:
  - `numero` (CharField, único, opcional): Número de factura formateado.
  - `tipo_pago` (CharField, choices: `CONTADO` / `CREDITO`, por defecto `CREDITO`): Tipo de pago.
  - `saldo` (DecimalField, por defecto `0.00`): Saldo pendiente de cobro.
  - `estado` (CharField, choices: `PENDIENTE` / `PAGADA` / `ANULADA`, por defecto `PENDIENTE`): Estado del cobro.
- Sobrescribir el método `save()` de `Invoice` para:
  - Autogenerar el campo `numero` con el formato `FAC-{self.id:06d}` si está vacío tras guardar.

#### [MODIFY] [views.py](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/billing/views.py)
- Modificar `InvoiceCreateView` (método `post`) para que, al guardar una nueva factura:
  - Obtenga el `payment_terms` del cliente.
  - Asigne `tipo_pago = 'CREDITO'` si el término de pago es a crédito (`credit_15`, `credit_30`, `credit_60`). De lo contrario, asigne `tipo_pago = 'CONTADO'`.
  - Inicialice `saldo` en el total de la factura si es a crédito, o `0.00` si es de contado.
  - Inicialice `estado` en `PENDIENTE` si es a crédito, o `PAGADA` si es de contado.

---

### Pagos App (Nueva Lógica de Cobros)

#### [MODIFY] [models.py](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/pagos/models.py)
- Definir el modelo `CobroFactura`:
  ```python
  from django.db import models
  from billing.models import Invoice

  class CobroFactura(models.Model):
      factura = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='cobros')
      fecha = models.DateField()
      valor = models.DecimalField(max_digits=10, decimal_places=2)
      observacion = models.TextField(blank=True)
  ```
- Implementar validaciones de negocio en el método `clean()`:
  - Validar que el valor del abono sea estrictamente mayor que cero (`valor > 0`). No permitir valores negativos o cero.
  - Validar que la factura no esté anulada o inactiva.
  - Validar que el valor del abono no supere el saldo pendiente de la factura.
- Implementar lógica transaccional en `save()` y `delete()`:
  - **Al guardar (crear/editar):**
    - Bloquear la fila de la factura usando `select_for_update()`.
    - Calcular la diferencia en el abono (si es edición) y restar del `saldo` de la factura.
    - Si el `saldo` de la factura llega a 0, actualizar su `estado = 'PAGADA'`. De lo contrario, `estado = 'PENDIENTE'`.
  - **Al eliminar:**
    - Validar que la factura no esté pagada completamente (o que el estado no sea `PAGADA`).
    - Validar que el saldo devuelto no cause inconsistencias (`saldo + valor > total`).
    - Sumar el valor del abono eliminado de vuelta al `saldo` de la factura y actualizar su `estado = 'PENDIENTE'`.

#### [NEW] [forms.py](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/pagos/forms.py)
- Crear el formulario `CobroFacturaForm` basado en el modelo `CobroFactura`.
- Incluir un campo widget de fecha de tipo HTML5 date y campos estilizados con Bootstrap.
- Validar reglas de negocio adicionales directamente en el formulario.

#### [MODIFY] [views.py](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/pagos/views.py)
- Crear las vistas basadas en clases (o funciones según conveniencia) para:
  1. **`FacturasPendientesListView`**: Consultar únicamente las facturas pendientes de pago (estado `PENDIENTE` e `is_active=True`).
  2. **`CobroFacturaCreateView`**: Registrar uno o varios abonos sobre una factura seleccionada.
  3. **`CobroFacturaUpdateView`**: Editar un pago ya registrado (con re-cálculo de saldo).
  4. **`CobroFacturaDeleteView`**: Eliminar un pago y restaurar el saldo de la factura (con validaciones de no-pagada).
  5. **`HistorialPagosListView`**: Mostrar el historial de cobros global o filtrado por factura.

#### [NEW] [urls.py](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/pagos/urls.py)
- Definir las rutas correspondientes:
  - `list/` -> Lista de facturas pendientes.
  - `pago/registrar/<int:invoice_id>/` -> Registrar pago.
  - `pago/editar/<int:pk>/` -> Editar pago.
  - `pago/eliminar/<int:pk>/` -> Eliminar pago.
  - `historial/` -> Historial global de cobros.
  - `historial/factura/<int:invoice_id>/` -> Historial de cobros de una factura.

#### [MODIFY] [Templates de pagos](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/pagos/templates/pagos/)
- Completar los archivos HTML vacíos utilizando la plantilla base del sistema (`billing/base.html`), con Bootstrap y estilos consistentes:
  - `pagos_list.html` (renombrado/utilizado para la lista de facturas pendientes de cobro y acciones de abonos).
  - `pagos_form.html` (formulario para registrar y editar abonos, mostrando detalles de la factura involucrada).
  - `pagos_delete.html` (confirmación de eliminación del abono).
  - `historial_pagos.html` (historial detallado de cobros con botones de editar y eliminar).

#### [MODIFY] [base.html](file:///c:/Users/18-P103/Downloads/sales_project%20%284%29/sales_project/billing/templates/billing/base.html)
- Agregar un menú desplegable de **Cobros** en el Navbar para los roles con permisos (`Ventas`, `Administrador`, `Gerente`):
  - Enlace a "Facturas Pendientes" (`pagos:facturas_pendientes`).
  - Enlace a "Historial de Pagos" (`pagos:historial_pagos`).

---

## Verification Plan

### Automated Actions & DB Migration
1. Generar los archivos de migración: `python manage.py makemigrations`
2. Aplicar las migraciones: `python manage.py migrate`
3. Ejecutar un script para inicializar los campos nuevos en las facturas existentes según su tipo de pago y total actual.

### Manual Verification
- Iniciar el servidor local: `python manage.py runserver`
- **Creación de Facturas**: Registrar una factura con condiciones de crédito y verificar que se guarde con estado `PENDIENTE` y saldo igual a su total. Registrar una de contado y verificar que su saldo sea `0.00` y estado `PAGADA`.
- **Registro de Abonos**: Registrar abonos sobre una factura a crédito y comprobar que el saldo pendiente disminuya correspondientemente.
- **Validaciones**:
  - Intentar abonar un valor negativo o cero y verificar el mensaje de error.
  - Intentar abonar un valor mayor al saldo y verificar el bloqueo.
  - Intentar registrar un pago sobre una factura anulada.
- **Cancelación**: Completar el pago de una factura a crédito (saldo llega a 0) y verificar que cambie su estado a `PAGADA`.
- **Edición de Abonos**: Editar el valor de un abono y verificar que el saldo se recalcule correctamente de forma transaccional.
- **Eliminación de Abonos**:
  - Eliminar un abono de una factura que aún no está totalmente cancelada y verificar que el saldo se re-incremente.
  - Intentar eliminar un abono de una factura que ya cambió a estado `PAGADA` y comprobar que el sistema lo impida.
