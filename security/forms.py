from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group, Permission

# === 1. REGISTRO DE USUARIO CON ROL ===
class UserRegisterForm(UserCreationForm):
    """Registro público: el usuario elige su rol al registrarse."""
    email = forms.EmailField(required=True, label='Correo electrónico')
    role = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        label='Rol',
        empty_label='-- Seleccione un rol --',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'password1', 'password2', 'role']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields:
            self.fields[f].widget.attrs['class'] = 'form-control'
        
        self.fields['username'].label = 'Nombre de usuario'
        self.fields['first_name'].label = 'Nombres'
        self.fields['last_name'].label = 'Apellidos'
        if 'password1' in self.fields:
            self.fields['password1'].label = 'Contraseña'
        if 'password2' in self.fields:
            self.fields['password2'].label = 'Confirmar contraseña'

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            # Asignar el rol elegido al nuevo usuario
            user.groups.add(self.cleaned_data['role'])
        return user

# === 2. EDICIÓN DE USUARIO (asignar roles) ===
class UserUpdateForm(forms.ModelForm):
    """El Administrador edita datos y roles de un usuario."""
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Roles',
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'is_active', 'groups']
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
            'is_active': 'Activo',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# === 3. ROLES (Group) CON SUS PERMISOS ===
class GroupForm(forms.ModelForm):
    """Crear/editar un rol y marcar sus permisos con checkboxes."""
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related('content_type'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Permisos',
    )

    class Meta:
        model = Group
        fields = ['name', 'permissions']
        labels = {
            'name': 'Nombre del Rol',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

# === 4. PERMISOS PERSONALIZADOS ===
class PermissionForm(forms.ModelForm):
    """Crear un permiso propio, ej: can_approve_invoice."""
    class Meta:
        model = Permission
        fields = ['name', 'codename', 'content_type']
        labels = {
            'name': 'Nombre del Permiso',
            'codename': 'Código de Permiso (codename)',
            'content_type': 'Tipo de Contenido (Modelo)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'codename': forms.TextInput(attrs={'class': 'form-control'}),
            'content_type': forms.Select(attrs={'class': 'form-select'}),
        }
