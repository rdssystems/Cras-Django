from django import forms

from cras.escolhas import SimNao
from cras.formularios import aplicar_classes, campo_de_data, configurar_cpf
from cras.validadores import validar_cpf

from .models import Certidao

CIDADE_PADRAO = 'UBERLÂNDIA - MG'


class CertidaoForm(forms.ModelForm):
    class Meta:
        model = Certidao
        fields = [
            'data_solicitacao', 'cidade', 'certidao_nascimento', 'certidao_casamento', 'certidao_obito',
            'com_averbacao', 'de_quem', 'filiacao', 'data_nascimento', 'cpf', 'telefone', 'endereco', 'bairro',
            'cad_unico', 'nis', 'quem_solicitou', 'parentesco',
            'data_recebimento', 'nome_contato', 'contato_em', 'data_entrega', 'entregue_para', 'observacoes',
        ]
        labels = {
            'data_solicitacao': 'Data', 'cidade': 'Cidade do cartório', 'de_quem': 'Nome',
            'quem_solicitou': 'Nome do responsável', 'parentesco': 'Parentesco com o registrado(a)',
        }
        widgets = {
            'data_solicitacao': campo_de_data(),
            'data_nascimento': campo_de_data(),
            'data_recebimento': campo_de_data(),
            'data_entrega': campo_de_data(),
            'cad_unico': forms.RadioSelect,
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cad_unico'].choices = SimNao.choices
        configurar_cpf(self.fields['cpf'])
        aplicar_classes(self)

    def clean_cpf(self):
        return validar_cpf(self.cleaned_data.get('cpf', '').strip())

    def clean(self):
        dados = super().clean()
        # Registros antigos da planilha não têm o tipo: o acompanhamento deles continua editável.
        exige_tipo = self.instance.pk is None or self.instance.ficha_preenchida
        if exige_tipo and not any(dados.get(campo) for campo, _ in Certidao.TIPOS):
            self.add_error(None, 'Marque a certidão solicitada.')
        return dados
