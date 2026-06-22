import re
from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Brand, ProductGroup, Supplier, Product, Customer, Invoice, InvoiceDetail

class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label='Correo electrónico',
        required=True,
        widget=forms.EmailInput(attrs={'class':'form-control', 'placeholder': 'Ej. juan.perez@example.com'})
    )
    first_name = forms.CharField(
        label='Nombre',
        max_length=100,
        widget=forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. Juan'})
    )
    last_name = forms.CharField(
        label='Apellido',
        max_length=100,
        widget=forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. Pérez'})
    )
    class Meta:
        model = User
        fields = ['username','first_name','last_name','email','password1','password2']
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields:
            self.fields[f].widget.attrs['class'] = 'form-control'
        if 'username' in self.fields:
            self.fields['username'].label = 'Nombre de usuario'
            self.fields['username'].widget.attrs['placeholder'] = 'Ej. juan_perez12'
        if 'password1' in self.fields:
            self.fields['password1'].label = 'Contraseña'
            self.fields['password1'].widget.attrs['placeholder'] = 'Escriba una contraseña segura'
        if 'password2' in self.fields:
            self.fields['password2'].label = 'Confirmar contraseña'
            self.fields['password2'].widget.attrs['placeholder'] = 'Repita la contraseña'

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name', 'description', 'image', 'is_active']
        labels = {
            'name': 'Nombre de la marca',
            'description': 'Descripción',
            'image': 'Imagen de la marca',
            'is_active': 'Activo',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. Samsung, Apple, Sony...'}),
            'description': forms.Textarea(attrs={'class':'form-control','rows':3, 'placeholder': 'Escriba una breve descripción de la marca...'}),
            'image': forms.FileInput(attrs={'class':'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }

class ProductGroupForm(forms.ModelForm):
    class Meta:
        model = ProductGroup
        fields = ['name', 'is_active']
        labels = {
            'name': 'Nombre de la categoría/grupo',
            'is_active': 'Activo',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. Lácteos, Electrónicos, Limpieza...'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_name', 'email', 'phone', 'address', 'is_active']
        labels = {
            'name': 'Nombre de la empresa',
            'contact_name': 'Nombre del contacto',
            'email': 'Correo electrónico',
            'phone': 'Teléfono/Celular',
            'address': 'Dirección',
            'is_active': 'Activo',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. Importadora Galarza S.A.'}),
            'contact_name': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. Ing. Carlos Mendoza'}),
            'email': forms.EmailInput(attrs={'class':'form-control', 'placeholder': 'Ej. ventas@importadoragalarza.com'}),
            'phone': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. 0998765432'}),
            'address': forms.Textarea(attrs={'class':'form-control', 'rows': 3, 'placeholder': 'Ej. Av. Amazonas N21-120 y Robles, Quito'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone_cleaned = re.sub(r'\s+|-', '', phone)
            if not re.match(r'^\d{10}$', phone_cleaned):
                raise forms.ValidationError("El teléfono del proveedor debe contener exactamente 10 dígitos numéricos.")
            return phone_cleaned
        return phone

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'brand', 'group', 'suppliers', 'unit_price', 'stock', 'image', 'is_active']
        labels = {
            'name': 'Nombre del producto',
            'description': 'Descripción',
            'brand': 'Marca',
            'group': 'Categoría/Grupo',
            'suppliers': 'Proveedores',
            'unit_price': 'Precio unitario (USD)',
            'stock': 'Stock/Inventario inicial',
            'image': 'Imagen del Producto',
            'is_active': 'Activo',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. Smart TV 55" QLED UHD'}),
            'description': forms.Textarea(attrs={'class':'form-control', 'rows': 3, 'placeholder': 'Ej. Pantalla de 55 pulgadas con resolución 4K, HDR10+, Smart Hub y conectividad Alexa integrada.'}),
            'brand': forms.Select(attrs={'class':'form-select'}),
            'group': forms.Select(attrs={'class':'form-select'}),
            'suppliers': forms.SelectMultiple(attrs={'class':'form-select'}),
            'unit_price': forms.NumberInput(attrs={'class':'form-control', 'placeholder': 'Ej. 649.99', 'min': '0.01', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class':'form-control', 'placeholder': 'Ej. 15', 'min': '0'}),
            'image': forms.FileInput(attrs={'class':'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
        help_texts = {
            'name': 'Ingrese un nombre descriptivo para el producto (solo letras y espacios).',
            'description': 'Detalle las especificaciones técnicas u otras notas importantes del producto.',
            'brand': 'Seleccione la marca fabricante del producto.',
            'group': 'Seleccione la categoría o grupo al que pertenece.',
            'suppliers': 'Seleccione uno o más proveedores. Mantenga presionada la tecla Ctrl para multiselección.',
            'unit_price': 'Ingrese el precio de venta unitario. Debe ser estrictamente mayor a 0.',
            'stock': 'Ingrese la cantidad inicial de inventario disponible (no puede ser negativo).',
            'image': 'Cargue una imagen del producto (opcional). El tamaño se ajustará automáticamente.',
            'is_active': 'Marque para habilitar el producto en el sistema de ventas.',
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['brand'].empty_label = "Seleccione una marca..."
        self.fields['group'].empty_label = "Seleccione una categoría/grupo..."

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s]+$', name):
                raise forms.ValidationError("El nombre del producto solo debe contener letras y espacios (sin números ni caracteres especiales).")
        return name

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise forms.ValidationError("El stock no puede ser negativo.")
        return stock

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get('unit_price')
        if unit_price is None or unit_price <= 0:
            raise forms.ValidationError("El precio unitario debe ser mayor que cero.")
        return unit_price

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['dni', 'first_name', 'last_name', 'email', 'phone', 'address', 'is_active']
        labels = {
            'dni': 'Identificación (DNI/RUC)',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
            'phone': 'Teléfono/Celular',
            'address': 'Dirección de domicilio',
            'is_active': 'Activo',
        }
        widgets = {
            'dni': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. 1726354890 o 1726354890001'}),
            'first_name': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. María Elena'}),
            'last_name': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. Pazmiño Rodríguez'}),
            'email': forms.EmailInput(attrs={'class':'form-control', 'placeholder': 'Ej. maria.paz@example.com'}),
            'phone': forms.TextInput(attrs={'class':'form-control', 'placeholder': 'Ej. 0998765432'}),
            'address': forms.Textarea(attrs={'class':'form-control', 'rows': 3, 'placeholder': 'Ej. Av. De la República E7-12 y Almagro, Quito'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if dni:
            if not re.match(r'^\d+$', dni):
                raise forms.ValidationError("La identificación (DNI/RUC) solo debe contener números.")
            if len(dni) not in [10, 13]:
                raise forms.ValidationError("La identificación debe tener exactamente 10 (DNI) o 13 (RUC) dígitos.")
        return dni

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            phone_cleaned = re.sub(r'\s+|-', '', phone)
            if not re.match(r'^\d+$', phone_cleaned):
                raise forms.ValidationError("El teléfono solo debe contener números.")
            return phone_cleaned
        return phone

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['customer']
        labels = {
            'customer': 'Cliente',
        }
        widgets = {
            'customer': forms.Select(attrs={'class':'form-select'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].empty_label = "Seleccione un cliente..."

InvoiceDetailFormSet = inlineformset_factory(
    Invoice,           # Modelo padre
    InvoiceDetail,     # Modelo hijo
    fields=['product', 'quantity', 'unit_price'],
    extra=3,           # 3 filas vacías para agregar
    can_delete=True,   # Checkbox para eliminar filas
    widgets={
        'product': forms.Select(attrs={'class': 'form-select'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
    }
)
