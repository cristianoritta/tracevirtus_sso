import re
import locale
from datetime import date, datetime
from django import template
from django.conf import settings


register = template.Library()

estados_siglas = {
"Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM",
"Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF", "Espírito Santo": "ES",
"Goiás": "GO", "Maranhão": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
"Minas Gerais": "MG", "Pará": "PA", "Paraíba": "PB", "Paraná": "PR",
"Pernambuco": "PE", "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
"Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR", "Santa Catarina": "SC",
"São Paulo": "SP", "Sergipe": "SE", "Tocantins": "TO"
}

# settings value
@register.simple_tag
def settings_value(name):

    conf = getattr(settings, 'DATABASES')
    print(conf)
    return conf['MYSQL_DB']        

@register.filter
def mask(value, mask):

    if value == None or value == '':
        return ''

    # 0001231-89.2019.8.25.0013.10.0001-19 - padrão do numero do mandado
    # 0001774-24.2018.8.07.0015 - padrão do numero do processo

    if mask == 'processo':
        string = re.sub("(\d{7})(\d{2})(\d{4})(\d{1})(\d{2})(\d{4})",
                        "\\1-\\2.\\3.\\4.\\5.\\6",
                        value)

    elif mask == 'mandado':
        string = re.sub("(\d{7})(\d{2})(\d{4})(\d{1})(\d{2})(\d{4})(\d{2})(\d{4})(\d{2})",
                        "\\1-\\2.\\3.\\4.\\5.\\6.\\7.\\8-\\9",
                        value)

    elif mask == 'cpf':
        if value is None or value == "None":
            string = ""
        else:
            string = re.sub("(\d{3})(\d{3})(\d{3})(\d{2})",
                            "\\1.\\2.\\3-\\4",
                            value)
        
    elif mask == 'cnpj':
        if value is None or value == "None":
            string = ""
        else:
            string = "".join(re.findall("\d+", value))
            string = re.sub("(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})",
                            "\\1.\\2.\\3/\\4-\\5",
                            value)

    elif mask == 'data':
        value = str(value)[0:10].replace('-', '').replace('/', '')
        string = re.sub("(\d{4})(\d{2})(\d{2})",
                        "\\3/\\2/\\1",
                        value)
    
    elif mask == 'hora':
        datetime_string = str(value)[:19]
        datetime_obj = datetime.strptime(datetime_string, "%Y-%m-%d %H:%M:%S") 
        string = datetime_obj.strftime("%H:%M:%S")

    elif mask == 'date_to_form':
        if value is None or str(value).lower() == "none":
            string = ""
        else:
            value = str(value)[0:10].replace('-', '')
            string = re.sub("(\d{4})(\d{2})(\d{2})",
                            "\\1-\\2-\\3",
                            value)

    elif mask == 'alert':
        types = {
            'error': 'danger',
            'success': 'success',
            'warning': 'warning',
            'info': 'info'
        }
        
        string = types.get(value, 'info')
        
    elif mask == 'md5':
        string = value * int(date.today().strftime('%d'))

        # Essa linha retorna um erro: <object supporting the buffer API required>
        # string = md5(value).digest()

    elif mask == 'upper':
        string = value.upper()

    elif mask == 'idade':
        try:
            if not isinstance(value, (datetime, date)):
                if isinstance(value, str) and '/' in value:
                    day, month, year = value.split('/')
                    value = datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')
                else:
                    return ''

            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))

            return f"{age} anos"

        except Exception as e:
            return ''

    elif mask == 'moeda':
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        string = locale.currency(value, grouping=True, symbol="R$")

    elif mask == 'tratar_none':
        string = value if value != None or "None" else ''

    elif mask == 'coma2dot':
        string = str(value).replace(',', '.')

    elif mask == 'versao':
        def substituir(m):
            return "<strong>" + m.group(1) + "</strong>"
        
        string = value.replace('#Atualizações#', '<span class="badge badge-round badge-primary badge-lg">Atualizações</span>').replace(
            '#Bugs#', '<span class="badge badge-round badge-danger badge-lg">Correção de erros</span>').replace(
                '#Novos recursos#', '<span class="badge badge-lg badge-round badge-success">Novos Recursos</span>')
        
        string = re.sub(r'\*\*(.*?)\*\*', substituir, string)
    
    elif mask == 'percent':
        string = str(int(value)) + '%'
    
    elif mask == 'split':
        return value.split(',')

    elif mask == 'numero':
        string = "".join(re.findall("\d+", value))
        
    elif mask == 'UF':
        estados = value.split(', ')
        siglas = [estados_siglas.get(estado.strip(), "Estado desconhecido") for estado in estados]
        string = ', '.join(siglas)

    # RETURN
    return string