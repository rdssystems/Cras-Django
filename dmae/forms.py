import re

from django import forms

from cras.formularios import (
    LinhaDePessoaForm, LinhaForm, aplicar_classes, campo_de_data, campo_do_modelo, configurar_cpf,
    formset_de_linhas,
)
from cras.validadores import validar_cpf

from .models import EvolucaoDmae, IsencaoDmae, MembroDmae

# Linhas em branco, como na ficha de papel (a evolução ganha uma e cresce pelo botão).
LINHAS_DA_COMPOSICAO = 2
LINHAS_DA_EVOLUCAO = 1

OPCOES_DE_MARCAR = (
    'solicitacao', 'estado_civil', 'cad_unico', 'tipo_imovel', 'situacao_imovel', 'mais_de_um_imovel',
)


class IsencaoDmaeForm(forms.ModelForm):
    """O requerimento. O resultado não entra aqui: é a etapa de deferimento."""

    class Meta:
        model = IsencaoDmae
        formfield_callback = campo_do_modelo(OPCOES_DE_MARCAR)
        exclude = ['resultado', 'servidor']
        labels = {'solicitacao': 'Tipo de solicitação'}
        widgets = {'parecer_social': forms.Textarea(attrs={'rows': 6, 'aria-label': 'Parecer social'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        configurar_cpf(self.fields['cpf'])
        self.fields['telefone'].widget.attrs['placeholder'] = '(34) '
        for n in (1, 2, 3):
            self.fields[f'consumo{n}_mes'].widget.attrs.update({'placeholder': 'MM/AAAA', 'inputmode': 'numeric'})
            self.fields[f'consumo{n}_m3'].widget.attrs['data-consumo'] = ''
        aplicar_classes(self)

    def clean_cpf(self):
        return validar_cpf(self.cleaned_data.get('cpf', '').strip())

    def _mes_e_ano(self, campo):
        valor = self.cleaned_data.get(campo, '').strip()
        if not valor:
            return ''
        partes = re.fullmatch(r'(\d{1,2})/(\d{4})', valor)
        if not partes or not 1 <= int(partes[1]) <= 12:
            raise forms.ValidationError('Use mês e ano, como 03/2026.')
        return f'{int(partes[1]):02d}/{partes[2]}'

    def clean_consumo1_mes(self):
        return self._mes_e_ano('consumo1_mes')

    def clean_consumo2_mes(self):
        return self._mes_e_ano('consumo2_mes')

    def clean_consumo3_mes(self):
        return self._mes_e_ano('consumo3_mes')


class MembroForm(LinhaDePessoaForm):
    class Meta:
        model = MembroDmae
        fields = ['nome', 'parentesco', 'idade', 'profissao', 'renda']


class EvolucaoForm(LinhaForm):
    class Meta:
        model = EvolucaoDmae
        fields = ['data', 'procedimento']
        widgets = {'data': campo_de_data(), 'procedimento': forms.Textarea(attrs={'rows': 2})}


def formset_de_membros(requerimento):
    return formset_de_linhas(requerimento, 'membros', MembroForm, LINHAS_DA_COMPOSICAO)


def formset_de_evolucao(requerimento):
    return formset_de_linhas(requerimento, 'evolucoes', EvolucaoForm, LINHAS_DA_EVOLUCAO)
