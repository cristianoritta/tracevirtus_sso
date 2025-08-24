from django import forms
from .models import Caso, Investigado, CasoInvestigado, Relatorio

class CasoForm(forms.ModelForm):
    class Meta:
        model = Caso
        fields = ['nome', 'numero', 'status', 'resumo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do caso'
            }),
            'numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número do caso'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'resumo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Resumo do caso',
            }),
        }
        labels = {
            'nome': 'Nome do Caso',
            'numero': 'Número do Caso',
            'status': 'Status',
            'resumo': 'Resumo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornando campos obrigatórios
        self.fields['nome'].required = True
        self.fields['numero'].required = True
        self.fields['resumo'].required = True

class InvestigadoForm(forms.ModelForm):
    class Meta:
        model = Investigado
        fields = ['nome', 'cpf_cnpj', 'tipo', 'dados_pessoais', 'enderecos', 'observacoes']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo'
            }),
            'cpf_cnpj': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'CPF ou CNPJ (apenas números)'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-control'
            }),
            'dados_pessoais': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dados pessoais adicionais'
            }),
            'enderecos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Endereços conhecidos'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações gerais'
            }),
        }
        labels = {
            'nome': 'Nome Completo',
            'cpf_cnpj': 'CPF/CNPJ',
            'tipo': 'Tipo de Pessoa',
            'dados_pessoais': 'Dados Pessoais',
            'enderecos': 'Endereços',
            'observacoes': 'Observações',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornando campos obrigatórios
        self.fields['nome'].required = True
        self.fields['cpf_cnpj'].required = True
        self.fields['tipo'].required = True

class CasoInvestigadoForm(forms.ModelForm):
    class Meta:
        model = CasoInvestigado
        fields = ['observacoes']
        widgets = {
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações específicas para este caso'
            }),
        }
        labels = {
            'observacoes': 'Observações sobre o investigado neste caso',
        }

class AdicionarInvestigadoForm(forms.Form):
    # Para pesquisar investigados existentes por CPF/CNPJ
    cpf_cnpj_existente = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite o CPF/CNPJ para buscar'
        }),
        label='Buscar Investigado Existente'
    )
    
    # Observações específicas para este caso
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observações específicas para este caso'
        }),
        label='Observações'
    ) 

class RelatorioForm(forms.ModelForm):
    class Meta:
        model = Relatorio
        fields = ['nome', 'descricao', 'tipo', 'status', 'arquivo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do relatório'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Descrição detalhada do relatório'
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-control',
                'choices': Relatorio.TIPO_CHOICES
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
                'choices': Relatorio.STATUS_CHOICES
            }),
            'arquivo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx'
            }),
        }
        labels = {
            'nome': 'Nome do Relatório',
            'descricao': 'Descrição',
            'tipo': 'Tipo',
            'status': 'Status',
            'arquivo': 'Arquivo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tornando campos obrigatórios
        self.fields['nome'].required = True
        self.fields['descricao'].required = True
        self.fields['tipo'].required = True
        self.fields['status'].required = True 