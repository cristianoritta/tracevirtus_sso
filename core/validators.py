from django.core.exceptions import ValidationError
from validate_docbr import CPF
import re

def validate_cpf(value):
    print(f"[DEBUG] validate_cpf - Valor recebido: {value} (tipo: {type(value)})")
    
    cpf = CPF()
    
    value = str(value)
    print(f"[DEBUG] validate_cpf - Valor como string: {value}")
    
    value = str(value).replace('.', '').replace('-', '').replace(' ', '')
    
    # Remove formatação
    value = ''.join(filter(str.isdigit, value))
    print(f"[DEBUG] validate_cpf - Valor após remover formatação: {value}")
    
    # Garante que o valor tenha 11 dígitos preenchendo com zeros à esquerda se necessário
    value = value.zfill(11)
    print(f"[DEBUG] validate_cpf - Valor após zfill: {value}")

    if not cpf.validate(value):
        print(f"[DEBUG] validate_cpf - CPF inválido segundo validate_docbr")
        raise ValidationError('CPF inválido. Por favor, insira um número válido.', code='invalid')
    
    print(f"[DEBUG] validate_cpf - CPF válido")
    # Validadores Django NÃO devem retornar valores
    
