from django.shortcuts import redirect
import requests
import time
from core import settings
from utils.jwt_funcoes import ler_jwt, carregar_chave_publica
from django.urls import resolve

class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ignora verificação para páginas públicas e rotas de autenticação
        public_paths = [
            '/login/', 
            '/static/',  
            '/media/',   
        ]
        
        # Verifica se é uma rota de autenticação
        try:
            route_name = resolve(request.path_info).url_name
            auth_routes = ['login', 'login_sso', 'login_sso_callback']
            if route_name in auth_routes:
                return self.get_response(request)
        except:
            pass
        
        # Verifica se o path atual começa com algum dos paths públicos
        if any(request.path.startswith(path) for path in public_paths):
            return self.get_response(request)

        # Verifica se existe token na sessão
        access_token = request.session.get('access_token')
        refresh_token = request.session.get('refresh_token')
        token_expires_in = request.session.get('token_expires_in')
        token_created_at = request.session.get('token_created_at', 0)

        if not access_token:
            # Se não há token e não está na página de login, redireciona
            if not request.path.startswith('/login'):
                return redirect('login')
            return self.get_response(request)

        # Calcula tempo restante para expiração
        tempo_atual = int(time.time())
        tempo_expiracao = token_created_at + token_expires_in
        tempo_restante = tempo_expiracao - tempo_atual


        # Verifica se o token está próximo de expirar (menos de 5 minutos)
        if tempo_restante < 300:
            try:
                # Tenta renovar o token usando refresh_token
                token_url = f"{settings.SSO_SERVER}/o/token/"
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": settings.CLIENT_ID,
                    "client_secret": settings.CLIENT_SECRET,
                }
                response = requests.post(token_url, data=data)
                
                if response.status_code == 200:
                    token_data = response.json()
                    
                    # Atualiza os tokens na sessão
                    request.session.update({
                        'access_token': token_data["access_token"],
                        'refresh_token': token_data.get("refresh_token", refresh_token),
                        'token_expires_in': token_data["expires_in"],
                        'token_created_at': int(time.time()),
                    })

                    # Se recebeu novo JWT, atualiza as informações do usuário
                    if "token_jwt" in token_data:
                        try:
                            public_key = carregar_chave_publica()
                            payload = ler_jwt(token_data["token_jwt"], public_key, verificar_assinatura=False)
                            
                            request.session.update({
                                'user_id': payload.get('user_id'),
                                'username': payload.get('username'),
                                'email': payload.get('email'),
                                'apps': payload.get('apps'),
                            })
                        except Exception as e:
                            print(f"[DEBUG] Erro ao decodificar novo JWT: {str(e)}")
                
                else:
                    print(f"[DEBUG] Erro ao renovar token: {response.json()}")
                    # Se falhou em renovar, força novo login
                    request.session.flush()
                    return redirect('login')

            except Exception as e:
                print(f"[DEBUG] Erro ao tentar renovar token: {str(e)}")
                request.session.flush()
                return redirect('login')

        response = self.get_response(request)
        return response 