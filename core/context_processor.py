from django.conf import settings

def app_name(request):
    """
    Adiciona o nome da aplicação ao contexto de todos os templates.
    """
    return {
        'APP_NAME': settings.APP_NAME
    }
