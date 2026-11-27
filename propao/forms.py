from django import forms

from cras.formularios import (
    LinhaDePessoaForm, LinhaForm, aplicar_classes, campo_de_data, campo_do_modelo, configurar_cpf,
    formset_de_linhas,
)
from cras.validadores import validar_cep, validar_cpf

from .models import PessoaProPao, ProcedimentoProPao, RequerimentoProPao

# A ficha de papel tem 8 linhas de pessoas; na tela começam 4 e o botão acrescenta as outras.
LINHAS_DA_COMPOSICAO = 4
LINHAS_DE_PROCEDIMENTO = 1

OPCOES_DE_MARCAR = ('solicitacao', 'estado_civil', 'cad_unico', 'situacao_imovel', 'segundo_imovel')


class RequerimentoProPaoForm(forms.ModelForm):
    """O requerimento. O resultado não entra aqui: é a etapa de deferimento."""

    # Declarado à mão para aceitar o CEP com ponto (a máscara 00000-000 é aplicada ao salvar).
    cep = forms.CharField(label='CEP', required=False, max_length=12)

    class Meta:
        model = RequerimentoProPao
        formfield_callback = campo_do_modelo(OPCOES_DE_MARCAR)
        exclude = ['resultado', 'servidor']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configurar_cpf(self.fields['cpf'])
        self.fields['cep'].widget.attrs.update({'inputmode': 'numeric', 'placeholder': '00000-000'})
        self.fields['telefone'].widget.attrs['placeholder'] = '(34) '
        aplicar_classes(self)

    def clean_cpf(self):
        return validar_cpf(self.cleaned_data.get('cpf', '').strip())

    def clean_cep(self):
        return validar_cep(self.cleaned_data.get('cep', '').strip())

    def clean(self):
        dados = super().clean()
        marcou_dono = dados.get('segundo_imovel_titular') or dados.get('segundo_imovel_conjuge')
        if marcou_dono and dados.get('segundo_imovel') != RequerimentoProPao.SegundoImovel.SIM:
            self.add_error('segundo_imovel', 'Para marcar Titular ou Cônjuge, escolha "Possui 2º imóvel".')
        return dados


class PessoaForm(LinhaDePessoaForm):
    class Meta:
        model = PessoaProPao
        fields = ['nome', 'parentesco', 'idade', 'ocupacao', 'renda']


class ProcedimentoForm(LinhaForm):
    class Meta:
        model = ProcedimentoProPao
        fields = ['data', 'procedimento']
        widgets = {'data': campo_de_data(), 'procedimento': forms.Textarea(attrs={'rows': 2})}


def formset_de_pessoas(requerimento):
    return formset_de_linhas(requerimento, 'pessoas', PessoaForm, LINHAS_DA_COMPOSICAO)


def formset_de_procedimentos(requerimento):
    return formset_de_linhas(requerimento, 'procedimentos', ProcedimentoForm, LINHAS_DE_PROCEDIMENTO)
