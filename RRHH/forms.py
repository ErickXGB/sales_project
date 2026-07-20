from django import forms
from django.forms import inlineformset_factory
from .models import Sobretiempo, SobretiempoDetalle, Prestamo, PrestamoDetalle, TipoPrestamo, Empleado

class SobretiempoForm(forms.ModelForm):
    class Meta:
        model = Sobretiempo
        fields = ['empleado', 'fecha_registro', 'total_horas', 'sueldo_mensual']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-select'}),
            'fecha_registro': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'total_horas': forms.NumberInput(attrs={'class': 'form-control bg-light', 'readonly': 'readonly'}),
            'sueldo_mensual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        }

    def clean_sueldo_mensual(self):
        sueldo = self.cleaned_data.get('sueldo_mensual')
        if sueldo is not None and sueldo <= 0:
            raise forms.ValidationError("El sueldo mensual debe ser mayor a cero.")
        return sueldo

    def clean_fecha_registro(self):
        fecha = self.cleaned_data.get('fecha_registro')
        from django.utils import timezone
        if fecha and fecha > timezone.localdate():
            raise forms.ValidationError("La fecha de registro no puede ser una fecha futura.")
        return fecha

    def clean(self):
        cleaned_data = super().clean()
        empleado = cleaned_data.get('empleado')
        fecha = cleaned_data.get('fecha_registro')
        if empleado and fecha:
            query = Sobretiempo.objects.filter(empleado=empleado, fecha_registro=fecha)
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                self.add_error('fecha_registro', f"El empleado {empleado} ya tiene un registro de sobretiempo para la fecha {fecha.strftime('%d/%m/%Y')}.")
        return cleaned_data


class BaseSobretiempoDetalleFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        from decimal import Decimal
        tipos_seleccionados = []
        total_horas_dia = Decimal('0.00')

        for form in self.forms:
            # Ignorar formularios vacíos o marcados para eliminación
            if self.can_delete and self._should_delete_form(form):
                continue
            if not form.cleaned_data:
                continue
            
            tipo = form.cleaned_data.get('tipo_sobretiempo')
            horas = form.cleaned_data.get('numero_horas')
            
            if tipo:
                if tipo not in tipos_seleccionados:
                    tipos_seleccionados.append(tipo)
            if horas:
                total_horas_dia += Decimal(str(horas))

        # 1. Validar que solo haya un tipo de sobretiempo por fecha
        if len(tipos_seleccionados) > 1:
            raise forms.ValidationError("Solo se permite registrar un tipo de sobretiempo por fecha.")

        # 2. Validar límite diario de 4 horas extras
        if total_horas_dia > Decimal('4.00'):
            raise forms.ValidationError(f"El límite de horas extras por día es de 4 horas. Actualmente ha ingresado {total_horas_dia} horas.")

        # 3. Validar límite semanal de 12 horas extras
        empleado = getattr(self.instance, 'empleado', None)
        fecha = getattr(self.instance, 'fecha_registro', None)
        
        if empleado and fecha:
            from datetime import timedelta
            from django.db.models import Sum
            
            start_of_week = fecha - timedelta(days=fecha.weekday()) # Lunes
            end_of_week = start_of_week + timedelta(days=6) # Domingo
            
            # Buscar otros detalles de sobretiempo de este empleado para la misma semana
            other_details = SobretiempoDetalle.objects.filter(
                sobretiempo__empleado=empleado,
                sobretiempo__fecha_registro__range=(start_of_week, end_of_week)
            )
            if self.instance.pk:
                other_details = other_details.exclude(sobretiempo=self.instance)
                
            total_horas_semanales_prev = other_details.aggregate(total=Sum('numero_horas'))['total'] or Decimal('0.00')
            total_semanal_completo = Decimal(str(total_horas_semanales_prev)) + total_horas_dia
            
            if total_semanal_completo > Decimal('12.00'):
                raise forms.ValidationError(
                    f"El límite de horas extras por semana es de 12 horas. "
                    f"Ya se han registrado {total_horas_semanales_prev} horas en la semana del {start_of_week.strftime('%d/%m/%Y')} al {end_of_week.strftime('%d/%m/%Y')}. "
                    f"Con este registro superaría el límite con un total de {total_semanal_completo} horas."
                )


SobretiempoDetalleFormSet = inlineformset_factory(
    Sobretiempo,
    SobretiempoDetalle,
    formset=BaseSobretiempoDetalleFormSet,
    fields=['tipo_sobretiempo', 'numero_horas'],
    extra=1,  # Inicia con una línea vacía
    can_delete=True,
    widgets={
        'tipo_sobretiempo': forms.Select(attrs={'class': 'form-select'}),
        'numero_horas': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
    }
)


class PrestamoForm(forms.ModelForm):
    class Meta:
        model = Prestamo
        fields = ['empleado', 'tipo_prestamo', 'fecha_prestamo', 'monto', 'numero_cuotas', 'estado']
        widgets = {
            'empleado': forms.Select(attrs={'class': 'form-select'}),
            'tipo_prestamo': forms.Select(attrs={'class': 'form-select'}),
            'fecha_prestamo': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'numero_cuotas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        if 'estado' in self.fields:
            self.fields['estado'].required = False
            self.fields['estado'].initial = 'PEND'
        if 'fecha_prestamo' in self.fields and not self.instance.pk:
            today_str = timezone.localdate().strftime('%Y-%m-%d')
            self.fields['fecha_prestamo'].initial = today_str
            self.fields['fecha_prestamo'].widget.attrs['min'] = today_str

    def clean_fecha_prestamo(self):
        fecha = self.cleaned_data.get('fecha_prestamo')
        from django.utils import timezone
        if not self.instance.pk and fecha and fecha < timezone.localdate():
            raise forms.ValidationError(f"La fecha del préstamo no puede ser anterior a la fecha actual ({timezone.localdate().strftime('%d/%m/%Y')}).")
        return fecha


    def clean(self):
        cleaned_data = super().clean()
        empleado = cleaned_data.get('empleado')
        tipo_prestamo = cleaned_data.get('tipo_prestamo')
        fecha_prestamo = cleaned_data.get('fecha_prestamo')
        monto = cleaned_data.get('monto')
        numero_cuotas = cleaned_data.get('numero_cuotas')
        estado = cleaned_data.get('estado') or 'PEND'

        if empleado and tipo_prestamo and monto and numero_cuotas:
            temp_prestamo = Prestamo(
                empleado=empleado,
                tipo_prestamo=tipo_prestamo,
                fecha_prestamo=fecha_prestamo or (self.instance.fecha_prestamo if self.instance else None),
                monto=monto,
                numero_cuotas=numero_cuotas,
                estado=estado
            )
            if self.instance and self.instance.pk:
                temp_prestamo.pk = self.instance.pk

            from django.core.exceptions import ValidationError
            try:
                temp_prestamo.clean()
            except ValidationError as e:
                if hasattr(e, 'error_dict'):
                    for field, field_errors in e.error_dict.items():
                        for err in field_errors:
                            self.add_error(field, err)
                else:
                    raise e
        return cleaned_data


class BasePrestamoDetalleFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        
        from decimal import Decimal
        total_valor_cuotas = Decimal('0.00')
        numeros_cuotas_vistos = set()
        fechas_vencimiento = []

        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if not form.cleaned_data:
                continue
            
            num = form.cleaned_data.get('numero_cuota')
            f_venc = form.cleaned_data.get('fecha_vencimiento')
            valor = form.cleaned_data.get('valor_cuota')
            saldo = form.cleaned_data.get('saldo_cuota')

            if num is not None:
                if num in numeros_cuotas_vistos:
                    raise forms.ValidationError(f"El número de cuota #{num} se encuentra duplicado.")
                numeros_cuotas_vistos.add(num)

            if valor is not None:
                if valor <= Decimal('0.00'):
                    raise forms.ValidationError("Todas las cuotas deben tener un valor mayor a cero.")
                total_valor_cuotas += Decimal(str(valor))

            if saldo is not None and valor is not None:
                if saldo < Decimal('0.00'):
                    raise forms.ValidationError("El saldo de una cuota no puede ser negativo.")
                if saldo > valor:
                    raise forms.ValidationError("El saldo de una cuota no puede superar el valor de la cuota.")

            if f_venc:
                fechas_vencimiento.append((num, f_venc))

        # Validar orden cronológico de fechas de vencimiento
        fechas_vencimiento.sort(key=lambda x: x[0] if x[0] else 0)
        for i in range(1, len(fechas_vencimiento)):
            if fechas_vencimiento[i][1] < fechas_vencimiento[i-1][1]:
                raise forms.ValidationError(
                    f"La fecha de vencimiento de la cuota #{fechas_vencimiento[i][0]} "
                    f"({fechas_vencimiento[i][1].strftime('%d/%m/%Y')}) no puede ser anterior a la cuota anterior "
                    f"({fechas_vencimiento[i-1][1].strftime('%d/%m/%Y')})."
                )

        # Si el préstamo ya existe y tiene monto_pagar definido, validar suma total
        prestamo_inst = getattr(self, 'instance', None)
        if prestamo_inst and prestamo_inst.pk and prestamo_inst.monto_pagar and total_valor_cuotas > 0:
            diferencia = abs(total_valor_cuotas - prestamo_inst.monto_pagar)
            if diferencia > Decimal('0.10'):
                raise forms.ValidationError(
                    f"La suma de las cuotas (${total_valor_cuotas:.2f}) debe coincidir con el monto total a pagar del préstamo (${prestamo_inst.monto_pagar:.2f})."
                )


PrestamoDetalleFormSet = inlineformset_factory(
    Prestamo,
    PrestamoDetalle,
    formset=BasePrestamoDetalleFormSet,
    fields=['numero_cuota', 'fecha_vencimiento', 'valor_cuota', 'saldo_cuota'],
    extra=0,
    can_delete=True,
    widgets={
        'numero_cuota': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        'fecha_vencimiento': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
        'valor_cuota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00'}),
        'saldo_cuota': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.00'}),
    }
)



