import locale


def moeda(valor):

    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    valor = locale.currency(valor, grouping=True, symbol=None)

    return valor
