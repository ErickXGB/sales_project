from django import forms
from django.forms import inlineformset_factory
from .models import Sobretiempo, SobretiempoDetalle

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

