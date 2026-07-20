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
