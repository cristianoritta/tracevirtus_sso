from django.conf import settings
from user.models import UserLogs
import json
from user_agents import parse
from user.models import CustomUser
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

class UserLogsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Verifica se existe um CPF na sessão
        cpf = request.session.get('cpf')
        if cpf:
            try:
                usuario_logado = int(cpf)
                # Cria o log apenas se houver um usuário logado
                UserLogs.objects.create(
                    usuario_id=usuario_logado,
                    ip=request.META.get('REMOTE_ADDR'),
                    porta=request.META.get('SERVER_PORT'),
                    device=request.META.get('HTTP_USER_AGENT'),
                    log=request.path,
                    request=request.POST or request.GET
                )
            except (ValueError, TypeError):
                # Se não conseguir converter para inteiro, ignora
                pass

    def __call__(self, request):
        response = self.get_response(request)

        # Verifica se existe um CPF na sessão
        cpf = request.session.get('cpf')
        if cpf:
            try:
                usuario_logado = int(cpf)
                usuario_ = CustomUser.objects.get(cpf=usuario_logado)
                
                # Só registra logs se o usuário estiver autenticado
                if usuario_.is_authenticated:
                    try:
                        # Obtém o IP e porta
                        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                        if x_forwarded_for:
                            ip = x_forwarded_for.split(',')[0].strip()
                        else:
                            ip = request.META.get('HTTP_X_REAL_IP')
                            if not ip:
                                ip = request.META.get('REMOTE_ADDR')
                        
                        # Obter a porta do cliente
                        porta = request.META.get('HTTP_REAL_PORT')
                        if not porta:
                            porta = request.META.get('REAL_PORT')
                        if not porta:
                            porta = request.META.get('REMOTE_PORT', 0)
                        
                        # Obter o User-Agent
                        user_agent_string = request.META.get('HTTP_USER_AGENT', '')
                        user_agent = parse(user_agent_string)

                        # Extraindo informações do User-Agent
                        browser = user_agent.browser.family
                        os = user_agent.os.family
                        device = user_agent.device.family
                        hostname = f'Navegador: {browser}, OS: {os}, Dispositivo: {device}'
                        
                        # Prepara os dados da requisição para salvar
                        request_data = {
                            'path': request.path,
                            'method': request.method,
                            'GET': dict(request.GET),
                            'POST': dict(request.POST),
                        }
                        
                        # Remove dados sensíveis
                        if 'password' in request_data['POST']:
                            request_data['POST']['password'] = '***'
                        
                        # Cria o log
                        UserLogs.objects.create(
                            usuario=usuario_,
                            ip=ip,
                            porta=porta,
                            device=hostname,
                            log=f"{request.method} {request.path}",
                            request=request_data,
                            created_by=usuario_,
                            updated_by=usuario_
                        )
                    except Exception as e:
                        # Em caso de erro, não impede a requisição de continuar
                        print(f"Erro ao salvar log: {str(e)}")
            except (ValueError, TypeError, CustomUser.DoesNotExist):
                # Se não conseguir converter para inteiro ou usuário não existe, ignora
                pass
        
        return response 