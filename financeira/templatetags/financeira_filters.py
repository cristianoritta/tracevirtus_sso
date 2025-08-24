from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter para acessar itens de dicionário
    Uso: {{ my_dict|get_item:key }}
    """
    return dictionary.get(key, '') 