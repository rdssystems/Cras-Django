from django import forms

from .models import Certidao


class CertidaoForm(forms.ModelForm):
    class Meta:
        model = Certidao
        fields = [
            'data_solicitacao', 'quem_solicitou', 'de_quem', 'telefone',
            'cidade', 'data_recebimento', 'nome_contato', 'contato_em',
            'data_entrega', 'entregue_para',
        ]
        widgets = {
            'data_solicitacao': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'quem_solicitou': forms.TextInput(attrs={'class': 'form-control'}),
            'de_quem': forms.TextInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'data_recebimento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nome_contato': forms.TextInput(attrs={'class': 'form-control'}),
            'contato_em': forms.TextInput(attrs={'class': 'form-control'}),
            'data_entrega': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'entregue_para': forms.TextInput(attrs={'class': 'form-control'}),
        }
