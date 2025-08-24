import locale
import pandas as pd


def moeda(valor):

    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    valor = locale.currency(valor, grouping=True, symbol=None)

    return valor


def processar_valor_monetario(valor_str):
    """
    Processa um valor monetário removendo símbolos, pontos de milhar, etc.
    e converte para float.
    """
    if not valor_str or pd.isna(valor_str):
        return 0.0
    
    # Converte para string se não for
    valor_str = str(valor_str).strip()
    
    if not valor_str:
        return 0.0
    
    # Se já for um número, retorna direto
    try:
        return float(valor_str)
    except ValueError:
        pass
    
    # Remove símbolos de moeda e espaços
    valor_limpo = valor_str.replace('R$', '').replace('$', '').replace(' ', '')
    
    # Verifica se usa vírgula como separador decimal (formato brasileiro)
    # Se tem ponto e vírgula, assume que ponto é milhar e vírgula é decimal
    if ',' in valor_limpo and '.' in valor_limpo:
        # Formato: 1.234.567,89
        valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
    elif ',' in valor_limpo and '.' not in valor_limpo:
        # Formato: 1234,89
        valor_limpo = valor_limpo.replace(',', '.')
    # Se só tem ponto, assume que é decimal se tem menos de 4 dígitos após o ponto
    elif '.' in valor_limpo:
        partes = valor_limpo.split('.')
        if len(partes) == 2 and len(partes[1]) <= 2:
            # Formato: 1234.89 (decimal)
            pass
        else:
            # Formato: 1.234.567 (milhar)
            valor_limpo = valor_limpo.replace('.', '')
    
    # Remove outros caracteres não numéricos exceto ponto e sinal de menos
    import re
    valor_limpo = re.sub(r'[^\d.-]', '', valor_limpo)
    
    try:
        return float(valor_limpo)
    except ValueError:
        return 0.0