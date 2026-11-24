from django import forms

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
        label='Resolvido na própria triagem (não entra na fila)', required=False,
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
        cpf = self.cleaned_data.get('cpf', '').strip()
        if not cpf:
            return ''
        if not cpf.isascii() or not cpf.isdigit():
            raise forms.ValidationError('Digite somente números, sem pontos ou traços.')
        if len(cpf) != 11:
            raise forms.ValidationError('O CPF deve ter exatamente 11 números.')
        if len(set(cpf)) == 1:
            raise forms.ValidationError('Informe um CPF válido.')

        numeros = [int(digito) for digito in cpf]
        primeiro = 11 - sum(numeros[indice] * (10 - indice) for indice in range(9)) % 11
        primeiro = 0 if primeiro >= 10 else primeiro
        segundo = 11 - sum(numeros[indice] * (11 - indice) for indice in range(10)) % 11
        segundo = 0 if segundo >= 10 else segundo
        if numeros[9:] != [primeiro, segundo]:
            raise forms.ValidationError('Informe um CPF válido.')
        return cpf

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
