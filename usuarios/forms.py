from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Usuario

CAMPOS = ['first_name', 'last_name', 'username', 'email', 'cargo', 'is_superuser']
ROTULOS = {
    'first_name': 'Nome',
    'last_name': 'Sobrenome',
    'username': 'Usuário (para entrar no sistema)',
    'email': 'E-mail',
    'cargo': 'Cargo',
    'is_superuser': 'Administrador do sistema (pode criar e editar contas)',
    'is_active': 'Conta ativa',
}


def estilizar(form):
    for nome, campo in form.fields.items():
        if isinstance(campo.widget, forms.CheckboxInput):
            continue
        classe = 'form-select' if isinstance(campo.widget, forms.Select) else 'form-control'
        campo.widget.attrs.setdefault('class', classe)
    form.fields['first_name'].required = True
    form.fields['cargo'].choices = [('', 'Selecione…'), *Usuario.Cargo.choices]


def validar_cargo(form, dados):
    # Quem não é administrador precisa de cargo: é o cargo que libera a fila psicossocial ou a administrativa.
    if not dados.get('is_superuser') and not dados.get('cargo'):
        form.add_error('cargo', 'Escolha o cargo.')


class UsuarioCriarForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = CAMPOS
        labels = ROTULOS
        help_texts = {'username': ''}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estilizar(self)

    def clean(self):
        dados = super().clean()
        validar_cargo(self, dados)
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.is_staff = usuario.is_superuser  # administrador também entra no /admin/
        if commit:
            usuario.save()
        return usuario


class UsuarioEditarForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = [*CAMPOS, 'is_active']
        labels = ROTULOS
        help_texts = {'username': '', 'is_superuser': '', 'is_active': ''}

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        estilizar(self)

    def clean(self):
        dados = super().clean()
        validar_cargo(self, dados)
        if self.editor and self.instance.pk == self.editor.pk:
            # Evita trancar o sistema sem nenhum administrador.
            if not dados.get('is_superuser'):
                self.add_error('is_superuser', 'Você não pode tirar o seu próprio acesso de administrador.')
            if not dados.get('is_active'):
                self.add_error('is_active', 'Você não pode desativar a sua própria conta.')
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.is_staff = usuario.is_superuser
        if commit:
            usuario.save()
        return usuario
