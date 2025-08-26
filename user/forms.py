from django import forms
from django.core.exceptions import ValidationError
from .models import Unidade, CustomUser


class CPFField(forms.CharField):
    """Campo personalizado para CPF que lida com formatação"""
    
    def to_python(self, value):
        """Converte o valor para Python antes da validação"""
        if value is None:
            return value
        
        # Remove formatação
        cpf_limpo = str(value).replace('.', '').replace('-', '').replace(' ', '')
        
        # Se não contém apenas dígitos, retorna o valor original para que clean_cpf possa lidar
        if not cpf_limpo.isdigit():
            return value
        
        # Se tem 11 dígitos, retorna como inteiro
        if len(cpf_limpo) == 11:
            return int(cpf_limpo)
        
        # Se tem menos de 11 dígitos, adiciona zeros à esquerda
        if len(cpf_limpo) < 11:
            cpf_limpo = cpf_limpo.zfill(11)
            return int(cpf_limpo)
        
        # Caso contrário, retorna o valor original
        return value
    
    def prepare_value(self, value):
        """Formata o valor para exibição no formulário"""
        if value is None:
            return value
        
        # Converte para string e adiciona zeros à esquerda se necessário
        cpf_str = str(value).zfill(11)
        
        # Formata o CPF para exibição
        return f"{cpf_str[:3]}.{cpf_str[3:6]}.{cpf_str[6:9]}-{cpf_str[9:]}"

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


class UsuarioForm(forms.ModelForm):
    password1 = forms.CharField(label='Senha', 
                              widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='Confirmar senha', 
                              widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    cpf = CPFField(
        label='CPF',
        widget=forms.TextInput(attrs={'class': 'form-control', 'data-mask': '000.000.000-00'})
    )

    class Meta:
        model = CustomUser
        fields = [
            'nome_completo', 'cpf', 'data_nascimento', 'email', 'telefone',
            'instituicao', 'unidade', 'cargo', 'cidade', 'uf_residencia',
            'is_admin', 'is_active'
        ]
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'data-mask': '(00) 00000-0000'}),
            'instituicao': forms.Select(attrs={'class': 'form-control form-select'}),
            'unidade': forms.Select(attrs={'class': 'form-control form-select'}),
            'cargo': forms.Select(attrs={'class': 'form-control form-select'}),
            'cidade': forms.Select(attrs={'class': 'form-control form-select'}),
            'uf_residencia': forms.Select(attrs={'class': 'form-control form-select'}),
            'is_admin': forms.CheckboxInput(attrs={'class': 'custom-control-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'custom-control-input'})
        }

    def __init__(self, *args, **kwargs):
        print(f"[DEBUG] UsuarioForm.__init__ - Iniciando")
        super().__init__(*args, **kwargs)
        print(f"[DEBUG] UsuarioForm.__init__ - Super().__init__ concluído")
        
        # Se for edição, não exige senha
        if self.instance.pk:
            print(f"[DEBUG] UsuarioForm.__init__ - É edição (instance.pk: {self.instance.pk})")
            del self.fields['password1']
            del self.fields['password2']
            
        # Não formata o CPF para evitar conflitos com a validação
        if self.instance.pk and self.instance.cpf:
            print(f"[DEBUG] UsuarioForm.__init__ - CPF da instância: {self.instance.cpf}")
        else:
            print(f"[DEBUG] UsuarioForm.__init__ - Não é edição ou não tem CPF")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("As senhas não conferem")
        return password2

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        print(f"[DEBUG] clean_cpf - CPF recebido: {cpf} (tipo: {type(cpf)})")
        
        if cpf:
            # Se já é um inteiro, valida diretamente
            if isinstance(cpf, int):
                cpf_str = str(cpf)
            else:
                # Remove formatação
                cpf_str = str(cpf).replace('.', '').replace('-', '').replace(' ', '')
            
            print(f"[DEBUG] clean_cpf - CPF para validação: {cpf_str}")
            
            # Verifica se contém apenas dígitos
            if not cpf_str.isdigit():
                print(f"[DEBUG] clean_cpf - CPF não contém apenas dígitos")
                raise forms.ValidationError("CPF deve conter apenas números")
            
            # Valida o CPF usando validate_docbr
            from validate_docbr import CPF
            cpf_validator = CPF()
            if not cpf_validator.validate(cpf_str):
                print(f"[DEBUG] clean_cpf - CPF inválido segundo validate_docbr")
                raise forms.ValidationError("CPF inválido. Por favor, insira um número válido.")
            
            # Retorna como inteiro
            cpf_int = int(cpf_str)
            print(f"[DEBUG] clean_cpf - CPF válido retornado: {cpf_int}")
            return cpf_int
        else:
            print(f"[DEBUG] clean_cpf - CPF é None ou vazio")
        return cpf

    def save(self, commit=True):
        print(f"[DEBUG] UsuarioForm.save - Iniciando save do formulário")
        user = super().save(commit=False)
        print(f"[DEBUG] UsuarioForm.save - User criado: {user}")
        print(f"[DEBUG] UsuarioForm.save - CPF do user: {user.cpf} (tipo: {type(user.cpf)})")
        
        if 'password1' in self.cleaned_data:
            print(f"[DEBUG] UsuarioForm.save - Definindo senha")
            user.set_password(self.cleaned_data["password1"])
        
        if commit:
            print(f"[DEBUG] UsuarioForm.save - Salvando user no banco")
            user.save()
            print(f"[DEBUG] UsuarioForm.save - User salvo com sucesso")
        
        return user