from django.core.exceptions import ValidationError
from validate_docbr import CPF
import re

def validate_cpf(value):
    cpf = CPF()
    
    value = ''.join(filter(str.isdigit, value))

    if not cpf.validate(value):
        raise ValidationError('CPF inválido. Por favor, insira um número válido.', code='invalid')
    