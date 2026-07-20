from django.test import TestCase
from django.core.exceptions import ValidationError
from django import forms
from datetime import date
from decimal import Decimal

from .models import Empleado, TipoSobretiempo, Sobretiempo, SobretiempoDetalle
from .forms import SobretiempoForm, SobretiempoDetalleFormSet

class SobretiempoValidationTests(TestCase):
    def setUp(self):
        # Crear datos básicos de prueba
        self.empleado = Empleado.objects.create(
            nombres="Empleado Test",
            sueldo=Decimal("600.00")
        )
        self.tipo_st50 = TipoSobretiempo.objects.create(
            codigo="ST50",
            descripcion="Sobretiempo 50%",
            factor=Decimal("1.50")
        )
        self.tipo_st100 = TipoSobretiempo.objects.create(
            codigo="ST100",
            descripcion="Sobretiempo 100%",
            factor=Decimal("2.00")
        )
        # Login superusuario
        from django.contrib.auth.models import User
        self.superuser = User.objects.create_superuser(username='admin', password='adminpassword')
        self.client.force_login(self.superuser)

    def test_uniqueness_employee_date_model(self):
        # Primer registro de sobretiempo (en el pasado)
        Sobretiempo.objects.create(
            empleado=self.empleado,
            fecha_registro=date(2026, 7, 13),
            sueldo_mensual=Decimal("600.00")
        )
        
        # Intentar crear otro en la misma fecha para el mismo empleado
        duplicate = Sobretiempo(
            empleado=self.empleado,
            fecha_registro=date(2026, 7, 13),
            sueldo_mensual=Decimal("600.00")
        )
        with self.assertRaises(ValidationError):
            duplicate.clean()

    def test_uniqueness_employee_date_form(self):
        # Primer registro
        Sobretiempo.objects.create(
            empleado=self.empleado,
            fecha_registro=date(2026, 7, 13),
            sueldo_mensual=Decimal("600.00")
        )
        
        # Intentar registrar via formulario
        form_data = {
            'empleado': self.empleado.id,
            'fecha_registro': '2026-07-13',
            'total_horas': 240,
            'sueldo_mensual': 600.00
        }
        form = SobretiempoForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('fecha_registro', form.errors)

    def test_single_overtime_type_validation(self):
        # Crear cabecera
        sobretiempo = Sobretiempo.objects.create(
            empleado=self.empleado,
            fecha_registro=date(2026, 7, 13),
            sueldo_mensual=Decimal("600.00")
        )
        
        # Intentar registrar detalles con múltiples tipos diferentes de sobretiempo
        formset_data = {
            'detalles-TOTAL_FORMS': '2',
            'detalles-INITIAL_FORMS': '0',
            'detalles-MIN_NUM_FORMS': '0',
            'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-tipo_sobretiempo': self.tipo_st50.id,
            'detalles-0-numero_horas': '2.00',
            'detalles-1-tipo_sobretiempo': self.tipo_st100.id,
            'detalles-1-numero_horas': '2.00',
        }
        formset = SobretiempoDetalleFormSet(data=formset_data, instance=sobretiempo)
        self.assertFalse(formset.is_valid())
        
        # Debe haber un error indicando que solo se permite un tipo de sobretiempo
        non_form_errors = formset.non_form_errors()
        self.assertTrue(any("Solo se permite registrar un tipo de sobretiempo por fecha" in err for err in non_form_errors))

    def test_daily_hours_limit_validation(self):
        sobretiempo = Sobretiempo.objects.create(
            empleado=self.empleado,
            fecha_registro=date(2026, 7, 13),
            sueldo_mensual=Decimal("600.00")
        )
        
        # Intentar registrar más de 4 horas extras (ej. 4.5 horas)
        formset_data = {
            'detalles-TOTAL_FORMS': '1',
            'detalles-INITIAL_FORMS': '0',
            'detalles-MIN_NUM_FORMS': '0',
            'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-tipo_sobretiempo': self.tipo_st50.id,
            'detalles-0-numero_horas': '4.50',
        }
        formset = SobretiempoDetalleFormSet(data=formset_data, instance=sobretiempo)
        self.assertFalse(formset.is_valid())
        non_form_errors = formset.non_form_errors()
        self.assertTrue(any("El límite de horas extras por día es de 4 horas" in err for err in non_form_errors))

    def test_weekly_hours_limit_validation(self):
        # Registrar 4 horas el Lunes 2026-07-13
        st1 = Sobretiempo.objects.create(empleado=self.empleado, fecha_registro=date(2026, 7, 13), sueldo_mensual=Decimal("600.00"))
        SobretiempoDetalle.objects.create(sobretiempo=st1, tipo_sobretiempo=self.tipo_st50, numero_horas=Decimal("4.00"))
        
        # Registrar 4 horas el Martes 2026-07-14
        st2 = Sobretiempo.objects.create(empleado=self.empleado, fecha_registro=date(2026, 7, 14), sueldo_mensual=Decimal("600.00"))
        SobretiempoDetalle.objects.create(sobretiempo=st2, tipo_sobretiempo=self.tipo_st50, numero_horas=Decimal("4.00"))

        # Registrar 4 horas el Miércoles 2026-07-15
        st3 = Sobretiempo.objects.create(empleado=self.empleado, fecha_registro=date(2026, 7, 15), sueldo_mensual=Decimal("600.00"))
        SobretiempoDetalle.objects.create(sobretiempo=st3, tipo_sobretiempo=self.tipo_st50, numero_horas=Decimal("4.00"))

        # En este punto el empleado tiene 12 horas acumuladas en la semana del lunes 13 de julio al domingo 19 de julio de 2026.
        # Intentar registrar 1 hora extra el Jueves 2026-07-16 (excediendo el límite semanal a 13 horas)
        st4 = Sobretiempo.objects.create(empleado=self.empleado, fecha_registro=date(2026, 7, 16), sueldo_mensual=Decimal("600.00"))
        formset_data = {
            'detalles-TOTAL_FORMS': '1',
            'detalles-INITIAL_FORMS': '0',
            'detalles-MIN_NUM_FORMS': '0',
            'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-tipo_sobretiempo': self.tipo_st50.id,
            'detalles-0-numero_horas': '1.00',
        }
        formset = SobretiempoDetalleFormSet(data=formset_data, instance=st4)
        self.assertFalse(formset.is_valid())
        non_form_errors = formset.non_form_errors()
        self.assertTrue(any("El límite de horas extras por semana es de 12 horas" in err for err in non_form_errors))

    def test_weekly_limit_view_flow(self):
        # Registrar 4 horas el Lunes 2026-07-13
        st1 = Sobretiempo.objects.create(empleado=self.empleado, fecha_registro=date(2026, 7, 13), sueldo_mensual=Decimal("600.00"))
        SobretiempoDetalle.objects.create(sobretiempo=st1, tipo_sobretiempo=self.tipo_st50, numero_horas=Decimal("4.00"))
        
        # Registrar 4 horas el Martes 2026-07-14
        st2 = Sobretiempo.objects.create(empleado=self.empleado, fecha_registro=date(2026, 7, 14), sueldo_mensual=Decimal("600.00"))
        SobretiempoDetalle.objects.create(sobretiempo=st2, tipo_sobretiempo=self.tipo_st50, numero_horas=Decimal("4.00"))

        # Registrar 4 horas el Miércoles 2026-07-15
        st3 = Sobretiempo.objects.create(empleado=self.empleado, fecha_registro=date(2026, 7, 15), sueldo_mensual=Decimal("600.00"))
        SobretiempoDetalle.objects.create(sobretiempo=st3, tipo_sobretiempo=self.tipo_st50, numero_horas=Decimal("4.00"))

        # Intentar crear un NUEVO sobretiempo vía POST en el view para el Jueves 2026-07-16 con 1 hora extra.
        # Esto debería fallar debido al límite semanal de 12 horas.
        from django.urls import reverse
        url = reverse('rrhh:sobretiempo_create')
        
        post_data = {
            'empleado': self.empleado.id,
            'fecha_registro': '2026-07-16',
            'total_horas': '240',
            'sueldo_mensual': '600.00',
            'detalles-TOTAL_FORMS': '1',
            'detalles-INITIAL_FORMS': '0',
            'detalles-MIN_NUM_FORMS': '0',
            'detalles-MAX_NUM_FORMS': '1000',
            'detalles-0-tipo_sobretiempo': self.tipo_st50.id,
            'detalles-0-numero_horas': '1.00',
        }
        
        response = self.client.post(url, data=post_data)
        # Como es inválido, no debe haber redirección exitosa. Debe renderizar la plantilla de error (status 200).
        self.assertEqual(response.status_code, 200)
        
        # Debe contener el mensaje de error de validación en el contexto de los formsets
        formset = response.context['detalles']
        non_form_errors = formset.non_form_errors()
        self.assertTrue(any("El límite de horas extras por semana es de 12 horas" in err for err in non_form_errors))


class PrestamoMasterDetailTests(TestCase):
    def setUp(self):
        from .models import TipoPrestamo, Prestamo, PrestamoDetalle
        self.empleado = Empleado.objects.create(
            nombres="Carlos Perez",
            sueldo=Decimal("800.00")
        )
        self.tipo_prestamo = TipoPrestamo.objects.create(
            descripcion="Préstamo Personal",
            tasa_interes=10
        )
        from django.contrib.auth.models import User
        self.superuser = User.objects.create_superuser(username='admin_test', password='password123')
        self.client.force_login(self.superuser)

    def test_prestamo_automatic_calculations_and_cuotas(self):
        from .models import Prestamo
        # Crear préstamo de $1000 a 10% de interés en 4 cuotas
        prestamo = Prestamo.objects.create(
            empleado=self.empleado,
            tipo_prestamo=self.tipo_prestamo,
            fecha_prestamo=date(2026, 7, 20),
            monto=Decimal("1000.00"),
            numero_cuotas=4
        )

        # 1. Verificar interés = 1000 * 10% = 100.00
        self.assertEqual(prestamo.interes, Decimal("100.00"))
        # 2. Verificar monto_pagar = 1000 + 100 = 1100.00
        self.assertEqual(prestamo.monto_pagar, Decimal("1100.00"))
        # 3. Verificar cuotas generadas automáticamente
        detalles = prestamo.detalles.all()
        self.assertEqual(detalles.count(), 4)
        
        # Cada cuota inicial = 1100 / 4 = 275.00
        total_cuotas = sum(d.valor_cuota for d in detalles)
        self.assertEqual(total_cuotas, Decimal("1100.00"))
        self.assertEqual(prestamo.saldo, Decimal("1100.00"))
        self.assertEqual(prestamo.estado, 'PEND')

    def test_cuota_payment_updates_saldo_and_estado(self):
        from .models import Prestamo
        prestamo = Prestamo.objects.create(
            empleado=self.empleado,
            tipo_prestamo=self.tipo_prestamo,
            fecha_prestamo=date(2026, 7, 20),
            monto=Decimal("1000.00"),
            numero_cuotas=2
        )
        # Total a pagar = $1100.00 en 2 cuotas de $550.00
        detalles = list(prestamo.detalles.all())
        self.assertEqual(len(detalles), 2)
        
        # Pagar la primera cuota
        cuota1 = detalles[0]
        cuota1.saldo_cuota = Decimal("0.00")
        cuota1.save()
        
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.saldo, Decimal("550.00"))
        self.assertEqual(prestamo.estado, 'PEND')
        
        # Pagar la segunda cuota
        cuota2 = detalles[1]
        cuota2.saldo_cuota = Decimal("0.00")
        cuota2.save()
        
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.saldo, Decimal("0.00"))
        self.assertEqual(prestamo.estado, 'PAG')

    def test_prestamo_create_view_renders(self):
        from django.urls import reverse
        url = reverse('rrhh:prestamo_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registrar Nuevo Préstamo")

    def test_tipo_prestamo_tasa_interes_validation(self):
        from .models import TipoPrestamo
        tp_invalid = TipoPrestamo(descripcion="Interés Inválido", tasa_interes=-5)
        with self.assertRaises(ValidationError):
            tp_invalid.clean()

        tp_high = TipoPrestamo(descripcion="Interés Excesivo", tasa_interes=60)
        with self.assertRaises(ValidationError):
            tp_high.clean()

    def test_prestamo_quirografario_validation(self):
        from .models import TipoPrestamo, Prestamo
        tp_quiro = TipoPrestamo.objects.create(descripcion="Préstamo Quirografario", tasa_interes=12)
        # Sueldo = $800, max quirografario monto = 800 * 12 = $9600
        p_invalid = Prestamo(
            empleado=self.empleado,
            tipo_prestamo=tp_quiro,
            fecha_prestamo=date(2026, 7, 20),
            monto=Decimal("15000.00"),
            numero_cuotas=12
        )
        with self.assertRaises(ValidationError):
            p_invalid.clean()

    def test_prestamo_solvency_capacity_validation(self):
        from .models import TipoPrestamo, Prestamo
        tp_hipo = TipoPrestamo.objects.create(descripcion="Préstamo Hipotecario", tasa_interes=8)
        # Sueldo = $800, max cuota permitida 50% = $400.
        # Solicitar $10000 en 5 cuotas -> cuota approx $2160 > $400
        p_excessive_quota = Prestamo(
            empleado=self.empleado,
            tipo_prestamo=tp_hipo,
            fecha_prestamo=date(2026, 7, 20),
            monto=Decimal("10000.00"),
            numero_cuotas=5
        )
    def test_prestamo_create_view_post_success(self):
        from django.urls import reverse
        from .models import Prestamo
        url = reverse('rrhh:prestamo_create')
        post_data = {
            'empleado': self.empleado.id,
            'tipo_prestamo': self.tipo_prestamo.id,
            'fecha_prestamo': '2026-07-20',
            'monto': '1000.00',
            'numero_cuotas': '10',
            'detalles-TOTAL_FORMS': '0',
            'detalles-INITIAL_FORMS': '0',
            'detalles-MIN_NUM_FORMS': '0',
            'detalles-MAX_NUM_FORMS': '1000',
        }
        response = self.client.post(url, data=post_data)
        self.assertEqual(response.status_code, 302)
        prestamo = Prestamo.objects.get(empleado=self.empleado, monto=Decimal('1000.00'))
        self.assertEqual(prestamo.detalles.count(), 10)

    def test_prestamo_past_date_validation(self):
        from .models import Prestamo
        from datetime import timedelta
        from django.utils import timezone
        past_date = timezone.localdate() - timedelta(days=5)
        p_past = Prestamo(
            empleado=self.empleado,
            tipo_prestamo=self.tipo_prestamo,
            fecha_prestamo=past_date,
            monto=Decimal("500.00"),
            numero_cuotas=2
        )
        with self.assertRaises(ValidationError):
            p_past.clean()

    def test_sequential_cuota_payment_enforcement(self):
        from django.urls import reverse
        from .models import Prestamo
        prestamo = Prestamo.objects.create(
            empleado=self.empleado,
            tipo_prestamo=self.tipo_prestamo,
            fecha_prestamo=date(2026, 7, 20),
            monto=Decimal("1000.00"),
            numero_cuotas=3
        )
        cuotas = list(prestamo.detalles.all())
        cuota1 = cuotas[0]
        cuota2 = cuotas[1]

        # Intentar pagar directamente la cuota #2 sin haber pagado la cuota #1
        url_pagar_cuota2 = reverse('rrhh:pagar_cuota', kwargs={'cuota_id': cuota2.id})
        response = self.client.get(url_pagar_cuota2)
        
        self.assertEqual(response.status_code, 302)
        cuota2.refresh_from_db()
        self.assertGreater(cuota2.saldo_cuota, Decimal('0.00'))


        # Pagar primero la cuota #1
        url_pagar_cuota1 = reverse('rrhh:pagar_cuota', kwargs={'cuota_id': cuota1.id})
        self.client.get(url_pagar_cuota1)
        cuota1.refresh_from_db()
        self.assertEqual(cuota1.saldo_cuota, Decimal('0.00'))

        # Ahora sí se debe permitir pagar la cuota #2
        self.client.get(url_pagar_cuota2)
        cuota2.refresh_from_db()
        self.assertEqual(cuota2.saldo_cuota, Decimal('0.00'))






