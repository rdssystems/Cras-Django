from django import forms

from cras.validadores import validar_cpf

from .models import PRIORIDADES, STATUS_DA_FILA, Atendimento, TipoFila


class AtendimentoForm(forms.ModelForm):
    """Triagem: em qual fila a pessoa entra e qual prioridade ela tem (o status sai da combinação)."""

    tipo_fila = forms.ChoiceField(
        label='Tipo de fila', choices=TipoFila.choices, initial=TipoFila.ADMINISTRATIVO,
        widget=forms.RadioSelect,
    )
    prioridade = forms.ChoiceField(
        label='Prioridade', choices=PRIORIDADES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    resolvido_na_triagem = forms.BooleanField(
        label='Orientações Realizadas na triagem (não entra na fila)', required=False,
    )

    class Meta:
        model = Atendimento
        fields = ['nome', 'cpf']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome completo', 'autofocus': True}),
            'cpf': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '00000000000',
                'inputmode': 'numeric',
                'maxlength': '11',
                'pattern': '[0-9]{11}',
                'data-cpf': '',
                'title': 'Digite os 11 números do CPF, sem pontos ou traços.',
            }),
        }

    def clean_cpf(self):
        return validar_cpf(self.cleaned_data.get('cpf', '').strip())

    def save(self, commit=True):
        atendimento = super().save(commit=False)
        if self.cleaned_data['resolvido_na_triagem']:
            atendimento.status = Atendimento.Status.ATENDIDO_TRIAGEM
        else:
            chave = (self.cleaned_data['tipo_fila'], self.cleaned_data['prioridade'])
            atendimento.status = STATUS_DA_FILA[chave]
        if commit:
            atendimento.save()
        return atendimento
