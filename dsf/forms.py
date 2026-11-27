from django import forms

from cras.formularios import (
    LinhaDePessoaForm, ReaisField, aplicar_classes, campo_do_modelo, configurar_cpf, formset_de_linhas,
)
from cras.validadores import validar_cpf

from .models import Dsf, MembroFamiliar

# Linhas em branco da composição familiar, como na ficha de papel.
LINHAS_DA_COMPOSICAO = 4

# Campos de escolha mostrados como opções de marcar, e não como lista suspensa.
OPCOES_DE_MARCAR = (
    'estado_civil', 'morou_outros_lugares', 'moradia', 'tipo_construcao', 'tem_deficiencia', 'gestante',
    'enfermidades', 'acompanhamento_medico', 'gasto_medicamentos', 'dmae', 'cemig', 'beneficio_bolsa_familia',
)


class DsfForm(forms.ModelForm):
    """A ficha do DSF. O parecer (resultado) não entra aqui: é a etapa de deferimento."""

    class Meta:
        model = Dsf
        formfield_callback = campo_do_modelo(OPCOES_DE_MARCAR)
        exclude = ['resultado', 'tecnico_responsavel', 'tecnico_legado']
        widgets = {
            'observacoes': forms.Textarea(attrs={'rows': 3}),
            'realidade_habitacao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficio_solicitado'].choices = [('', 'Selecione…'), *Dsf.Beneficio.choices]
        configurar_cpf(self.fields['cpf'])
        aplicar_classes(self)

    def clean_cpf(self):
        return validar_cpf(self.cleaned_data.get('cpf', '').strip())


class MembroForm(LinhaDePessoaForm):
    class Meta:
        model = MembroFamiliar
        fields = ['nome', 'parentesco', 'idade', 'ocupacao', 'escolaridade', 'renda']


def formset_de_membros(dsf):
    return formset_de_linhas(dsf, 'membros', MembroForm, LINHAS_DA_COMPOSICAO)
