"""Peças de formulário usadas por mais de um app."""
import re
from decimal import Decimal

from django import forms
from django.core.validators import MaxValueValidator
from django.db import models


def campo_de_data():
    """<input type="date"> só mostra o valor gravado se ele vier no formato ISO (o pt-br usaria dd/mm/aaaa)."""
    return forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})


class ReaisField(forms.DecimalField):
    """Valor em reais digitado do jeito brasileiro: "1.412,50", "1412,5", "R$ 600" ou "600.00"."""

    widget = forms.TextInput(attrs={'inputmode': 'decimal'})

    def to_python(self, value):
        if isinstance(value, str):
            value = value.replace('R$', '').replace(' ', '').replace('\xa0', '')
            if ',' in value:
                value = value.replace('.', '').replace(',', '.')
            elif re.fullmatch(r'\d{1,3}(\.\d{3})+', value):
                value = value.replace('.', '')  # "1.412" é mil quatrocentos e doze
        return super().to_python(value)

    def prepare_value(self, value):
        if isinstance(value, Decimal):
            return f'{value:.2f}'.replace('.', ',')
        return value


def campo_do_modelo(opcoes_de_marcar=()):
    """`formfield_callback` das fichas: reais, datas e as escolhas mostradas como opções de marcar."""

    def criar(campo, **kwargs):
        if isinstance(campo, models.DecimalField):
            kwargs.update(form_class=ReaisField, min_value=0, widget=ReaisField.widget)
        elif isinstance(campo, models.DateField):
            kwargs['widget'] = campo_de_data()
        elif campo.name in opcoes_de_marcar:
            kwargs.update(widget=forms.RadioSelect, choices=campo.choices)
        return campo.formfield(**kwargs)

    return criar


def configurar_cpf(campo):
    # maxlength 14 deixa colar o CPF com pontos; o ficha.js tira o que não é número.
    campo.widget.attrs.update({'inputmode': 'numeric', 'maxlength': '14', 'data-cpf': ''})


def aplicar_classes(form):
    for campo in form.fields.values():
        if isinstance(campo.widget, (forms.RadioSelect, forms.CheckboxInput)):
            continue
        classe = 'form-select' if isinstance(campo.widget, forms.Select) else 'form-control'
        campo.widget.attrs['class'] = classe


class LinhaForm(forms.ModelForm):
    """Linha de uma tabela da ficha: o título da coluna vira o rótulo acessível do campo."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        aplicar_classes(self)
        for campo in self.fields.values():
            campo.widget.attrs['aria-label'] = campo.label


class LinhaDePessoaForm(LinhaForm):
    """Linha da composição familiar."""

    renda = ReaisField(label='Renda (R$)', required=False, min_value=0, max_digits=10, decimal_places=2)
    idade = forms.IntegerField(label='Idade', required=False, min_value=0, validators=[MaxValueValidator(130)])


def formset_de_linhas(registro, relacao, form, linhas):
    """Formset de uma tabela da ficha, completando até `linhas` linhas na tela."""
    existentes = getattr(registro, relacao).count() if registro.pk else 0
    return forms.inlineformset_factory(
        type(registro), form._meta.model, form=form, can_delete=True, extra=max(linhas - existentes, 0),
    )
