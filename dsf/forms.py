from django import forms

from .models import Dsf


class DsfForm(forms.ModelForm):
    class Meta:
        model = Dsf
        fields = ['nome', 'beneficio_solicitado', 'data', 'resultado']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'beneficio_solicitado': forms.Select(attrs={'class': 'form-select'}),
            'data': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'resultado': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['beneficio_solicitado'].choices = [('', 'Selecione…'), *Dsf.Beneficio.choices]
