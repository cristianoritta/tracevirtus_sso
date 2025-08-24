def validar_e_limpar_cpf_cnpj(numero):
    """
    Limpa e valida um número de CPF ou CNPJ.
    Retorna o número limpo se válido, ou None se inválido.
    """
    if not numero:
        return None
        
    # Remove caracteres não numéricos
    numero_limpo = ''.join(filter(str.isdigit, str(numero)))
    
    # Verifica se é CPF (11 dígitos) ou CNPJ (14 dígitos)
    if len(numero_limpo) == 11:  # CPF
        # Verifica se todos os dígitos são iguais
        if len(set(numero_limpo)) == 1:
            return None
            
        # Calcula primeiro dígito verificador
        soma = 0
        peso = 10
        for i in range(9):
            soma += int(numero_limpo[i]) * peso
            peso -= 1
        digito1 = 11 - (soma % 11)
        if digito1 > 9:
            digito1 = 0
            
        # Calcula segundo dígito verificador    
        soma = 0
        peso = 11
        for i in range(10):
            soma += int(numero_limpo[i]) * peso
            peso -= 1
        digito2 = 11 - (soma % 11)
        if digito2 > 9:
            digito2 = 0
            
        # Verifica se os dígitos calculados são iguais aos dígitos informados
        if (int(numero_limpo[9]) == digito1 and int(numero_limpo[10]) == digito2):
            return numero_limpo
            
    elif len(numero_limpo) == 14:  # CNPJ
        # Verifica se todos os dígitos são iguais
        if len(set(numero_limpo)) == 1:
            return None
            
        # Calcula primeiro dígito verificador
        soma = 0
        peso = [5,4,3,2,9,8,7,6,5,4,3,2]
        for i in range(12):
            soma += int(numero_limpo[i]) * peso[i]
        digito1 = 11 - (soma % 11)
        if digito1 > 9:
            digito1 = 0
            
        # Calcula segundo dígito verificador
        soma = 0
        peso = [6,5,4,3,2,9,8,7,6,5,4,3,2]
        for i in range(13):
            soma += int(numero_limpo[i]) * peso[i]
        digito2 = 11 - (soma % 11)
        if digito2 > 9:
            digito2 = 0
            
        # Verifica se os dígitos calculados são iguais aos dígitos informados
        if (int(numero_limpo[12]) == digito1 and int(numero_limpo[13]) == digito2):
            return numero_limpo
    
    # Se não for CPF ou CNPJ válido, retorna None
    return None
