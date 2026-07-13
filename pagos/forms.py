from django import forms
from django.utils import timezone
from .models import CobroFactura

class CobroFacturaForm(forms.ModelForm):
    class Meta:
        model = CobroFactura
        fields = ['fecha', 'valor', 'observacion']
        widgets = {
            'fecha': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                    'placeholder': 'Seleccione fecha y hora'
                },
                format='%Y-%m-%dT%H:%M'
            ),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 100.00',
                'min': '0.01',
                'step': '0.01'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escriba una observación sobre este abono...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Formatear fecha y hora para datetime-local
        if self.instance and self.instance.pk and self.instance.fecha:
            self.initial['fecha'] = timezone.localtime(self.instance.fecha).strftime('%Y-%m-%dT%H:%M')
        elif not self.initial.get('fecha'):
            self.initial['fecha'] = timezone.localtime().strftime('%Y-%m-%dT%H:%M')
        else:
            val = self.initial.get('fecha')
            if not isinstance(val, str):
                self.initial['fecha'] = timezone.localtime(val).strftime('%Y-%m-%dT%H:%M')


from .models import PagoCompra

class PagoCompraForm(forms.ModelForm):
    class Meta:
        model = PagoCompra
        fields = ['fecha', 'valor', 'observacion']
        widgets = {
            'fecha': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'
            ),
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 100.00',
                'min': '0.01',
                'step': '0.01'
            }),
            'observacion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Escriba una observación sobre este abono...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.fecha:
            self.initial['fecha'] = self.instance.fecha.strftime('%Y-%m-%d')
        elif not self.initial.get('fecha'):
            from django.utils import timezone
            self.initial['fecha'] = timezone.localdate().strftime('%Y-%m-%d')
        else:
            val = self.initial.get('fecha')
            if not isinstance(val, str):
                self.initial['fecha'] = val.strftime('%Y-%m-%d')
