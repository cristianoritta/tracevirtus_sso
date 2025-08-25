from django import forms
from .models import Unidade

class UnidadeForm(forms.ModelForm):
    class Meta:
        model = Unidade
        fields = ['instituicao', 'nome', 'endereco', 'numero', 'complemento', 'bairro', 'cep', 'parent']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
            
        # Se a instância já existe, filtra as unidades da mesma instituição
        if self.instance and self.instance.pk and self.instance.instituicao:
            self.fields['parent'].queryset = Unidade.objects.filter(
                instituicao=self.instance.instituicao
            ).exclude(pk=self.instance.pk)
        else:
            self.fields['parent'].queryset = Unidade.objects.none()
            
        # Torna o campo parent opcional
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = "Nenhuma"
