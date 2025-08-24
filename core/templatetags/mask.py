import re
import locale
from datetime import date, datetime
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe


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
        try:
            # Tenta usar locale primeiro
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
            string = locale.currency(value, grouping=True, symbol="R$")
        except:
            # Fallback para formatação manual
            if value is None or value == "":
                string = "R$ 0,00"
            else:
                try:
                    # Converte para float
                    valor = float(value)
                    # Formata com 2 casas decimais
                    valor_str = f"{valor:.2f}"
                    # Separa parte inteira e decimal
                    partes = valor_str.split('.')
                    parte_inteira = partes[0]
                    parte_decimal = partes[1] if len(partes) > 1 else "00"
                    
                    # Adiciona separadores de milhares
                    if len(parte_inteira) > 3:
                        parte_inteira = re.sub(r'(\d)(?=(\d{3})+(?!\d))', r'\1.', parte_inteira[::-1])[::-1]
                    
                    string = f"R$ {parte_inteira},{parte_decimal}"
                except:
                    string = "R$ 0,00"



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

    elif mask == 'cpf_cnpj':
        if value is None or value == "None" or value == "" or value == "N/A":
            string = ""
        else:
            # Remove caracteres não numéricos
            value = "".join(re.findall("\d+", str(value)))
            
            # Aplica máscara baseada no tamanho
            if len(value) <= 11:
                value = str(value).zfill(11)
                string = re.sub("(\d{3})(\d{3})(\d{3})(\d{2})",
                                "\\1.\\2.\\3-\\4",
                                value)
            else:
                string = re.sub("(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})",
                                "\\1.\\2.\\3/\\4-\\5",
                                value)

    # RETURN
    return string


@register.filter
def real(value):
    """
    Máscara específica para valores monetários brasileiros (R$)
    Formato: R$ 1.234,56
    """
    if value is None or value == "" or str(value).lower() in ['none', 'nan']:
        return "R$ 0,00"
    else:
        try:
            # Remove caracteres não numéricos exceto ponto e vírgula
            valor_limpo = re.sub(r'[^\d.,]', '', str(value))
            
            # Se tem vírgula, assume que é decimal
            if ',' in valor_limpo:
                valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
            else:
                # Se só tem ponto, assume que é decimal
                valor_limpo = valor_limpo.replace(',', '')
            
            # Converte para float
            valor = float(valor_limpo)
            
            # Formata com 2 casas decimais
            valor_str = f"{valor:.2f}"
            
            # Separa parte inteira e decimal
            partes = valor_str.split('.')
            parte_inteira = partes[0]
            parte_decimal = partes[1] if len(partes) > 1 else "00"
            
            # Adiciona separadores de milhares (ponto)
            if len(parte_inteira) > 3:
                # Inverte a string, aplica os separadores e inverte de volta
                parte_inteira = parte_inteira[::-1]  # inverte a string
                parte_inteira = '.'.join(parte_inteira[i:i+3] for i in range(0, len(parte_inteira), 3))
                parte_inteira = parte_inteira[::-1]  # inverte de volta
            
            return f"R$ {parte_inteira},{parte_decimal}"
            
        except (ValueError, TypeError):
            return "R$ 0,00"


@register.filter
def markdown(value):
    """
    Filtro para renderizar markdown em HTML
    """
    if not value:
        return ""
    
    try:
        # Importa markdown apenas quando necessário
        import markdown as md
        
        # Configurações básicas do markdown
        md_extensions = [
            'markdown.extensions.codehilite',
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.toc',
            'markdown.extensions.nl2br'
        ]
        
        # Converte markdown para HTML
        html = md.markdown(str(value), extensions=md_extensions)
        
        # Marca como seguro para renderização
        return mark_safe(html)
        
    except ImportError:
        # Se markdown não estiver instalado, retorna o texto original
        return str(value)
    except Exception:
        # Em caso de erro, retorna o texto original
        return str(value)