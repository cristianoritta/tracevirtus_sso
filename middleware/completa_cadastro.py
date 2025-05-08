from datetime import datetime
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages
from user.models import CustomUser
from django.urls import reverse, NoReverseMatch


class CadastroMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        excluded_paths = ["/login/", "/login_sso/", "/login_sso/callback/", "/logout_sso", "/admin/", "/usuario/ajax/"]
        try:
            completar_cadastro_url = reverse('completar_cadastro')
            excluded_paths.append(completar_cadastro_url)
        except NoReverseMatch:
            print("Alerta: Nome da URL 'completar_cadastro' não encontrado para exclusão no CadastroMiddleware.")

        if any(request.path.startswith(path) for path in excluded_paths):
            return response

        cpf = request.session.get('cpf')
        if cpf:
            try:
                usuario_cpf = int(cpf)
                user = CustomUser.objects.get(cpf=usuario_cpf)

                usuario_attrs_to_check = [
                    user.nome_completo,
                    user.telefone, 
                    user.email,
                    user.instituicao,
                    user.cargo,
                    user.cidade,
                    user.uf_residencia
                ]

                is_incomplete = any(attr is None for attr in usuario_attrs_to_check)

                if is_incomplete:
                    messages.info(request, 'Preencha todos os dados do cadastro.')
                    return redirect('completar_cadastro')

            except CustomUser.DoesNotExist:
                messages.info(request, 'Bem-vindo! Por favor, complete seu cadastro para continuar.')
                return redirect('completar_cadastro')

            except Exception as e:
                print(f"Erro no CadastroMiddleware ao verificar usuário {cpf}: {e}")
                messages.error(request, 'Ocorreu um erro ao verificar seus dados cadastrais. Tente novamente mais tarde.')

        return response