from django.contrib import messages
from django.shortcuts import redirect
from app.models import CasoAtivoUsuario


def _buscar_caso_ativo(request: 'Request') -> 'Caso':
    """Busca o caso ativo a partir da sessão do usuário.

    Esta função verifica se há um caso ativo na sessão do usuário.
    Se não houver, busca o primeiro caso ativo disponível.

    Args:
        request (Request): Requisição HTTP atual.

    Returns:
        Caso: Instância do caso ativo.
    """
    # Busca o caso ativo para o Usuario
    caso_ativo = CasoAtivoUsuario.objects.filter(usuario=request.user).first()

    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')

    return caso_ativo.caso
