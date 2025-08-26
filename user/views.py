from user.models import CustomUser, Instituicao, Cargo, Cidades, UFs, CategoriaInstituicao
from django.contrib import messages
from .forms import UsuarioForm
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.db import transaction
import logging
from django.contrib.auth import login
import requests
import time
from core import settings
from utils.jwt_funcoes import ler_jwt, carregar_chave_publica
from django.core.paginator import Paginator
from user.models import UserLogs
from django.contrib.auth.decorators import login_required, user_passes_test
from user.models import Unidade
from user.forms import UnidadeForm

logger = logging.getLogger(__name__)


def login_view(request):
    try:
        # Verifica se já existe um token válido
        access_token = request.session.get('access_token')
        token_created_at = request.session.get('token_created_at', 0)
        token_expires_in = request.session.get('token_expires_in')

        if access_token and token_created_at and token_expires_in:
            # Verifica se o token ainda é válido
            tempo_atual = int(time.time())
            tempo_expiracao = token_created_at + token_expires_in

            if tempo_atual < tempo_expiracao:
                # Verifica se o usuário está autenticado no Django
                if request.user.is_authenticated:
                    logger.info(
                        "Token válido e usuário autenticado - redirecionando para home")
                    return redirect('home')
                else:
                    logger.info(
                        "Token válido mas usuário não autenticado no Django - mantendo na página de login")
            else:
                logger.info("Token expirado encontrado - limpando sessão")
                request.session.flush()
    except Exception as e:
        logger.error(f"Erro ao verificar token: {str(e)}")
        request.session.flush()

    return render(request, 'auth/login.html')

# Rota para redirecionar ao servidor SSO


def login_sso(request):
    try:
        logger.info("Iniciando login SSO")

        sso_url = f"{settings.SSO_SERVER}/o/authorize/"
        params = {
            "client_id": settings.CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.REDIRECT_URI,
            "scope": "read write",
            "code_challenge": settings.CODE_CHALLENGE,
            "code_challenge_method": "S256",
        }
        url = f"{sso_url}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"
        logger.info(f"URL de redirecionamento SSO: {url}")
        return redirect(url)
    except Exception as e:
        logger.error(f"Erro ao iniciar login SSO: {str(e)}")
        messages.error(request, "Erro ao iniciar processo de login")
        return redirect('login')

# Rota para lidar com o callback


def login_sso_callback(request):
    try:
        logger.info("Callback SSO recebido")
        code = request.GET.get("code")
        if not code:
            logger.warning("Código de autorização não encontrado")
            return HttpResponse("Erro: Código de autorização não encontrado.", status=400)

        logger.info(f"Código de autorização recebido: {code}")

        # Troca do código por um token
        token_url = f"{settings.SSO_SERVER}/o/token/"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.REDIRECT_URI,
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "code_verifier": settings.CODE_VERIFIER,
        }
        logger.info("Solicitando token")
        response = requests.post(token_url, data=data)

        if response.status_code == 200:
            token_data = response.json()
            logger.info("Token obtido com sucesso")
            jwt_token = token_data.get("token_jwt")
            logger.info("JWT Token recebido")

            try:
                # Carrega a chave pública usando a função existente
                public_key = carregar_chave_publica()

                # Decodifica o token sem verificação de assinatura
                payload = ler_jwt(jwt_token, public_key,
                                  verificar_assinatura=True)
                logger.info("Payload decodificado com sucesso")

                # Verifica se já existe um usuário local com o CPF
                cpf = int(payload.get('cpf'))
                email = payload.get('email')

                #############################################################################################################
                # TODO: TEMPORARIAMENTE, VALIDAR EMAIL PARA O DOMÍNIO @mpce.mp.br
                #############################################################################################################
                if not email.endswith('@mpce.mp.br') \
                    and not email == 'tiano.ritta@gmail.com' \
                   and not email == 'alvarolucasno@gmail.com' \
                        and not email == 'cristiano-ritta@pc.rs.gov.br':

                    logger.error(
                        f"Tentativa de login com email não autorizado: {email}")
                    messages.error(
                        request, "Apenas emails do domínio @mpce.mp.br são permitidos.")
                    return redirect('login')
                #############################################################################################################

                try:
                    usuario_local = CustomUser.objects.get(cpf=cpf)
                    logger.info(f"Usuário local encontrado: {cpf}")

                    # Faz o login do usuário local
                    login(request, usuario_local)
                    logger.info("Usuário local logado com sucesso")

                except CustomUser.DoesNotExist:
                    usuario_local = None
                    logger.info("Usuário local não encontrado")

                # Salvar informações do usuário na sessão
                for key, value in payload.items():
                    request.session.update({key: value})

                request.session.update({
                    'access_token': token_data["access_token"],
                    'refresh_token': token_data["refresh_token"],
                    'token_expires_in': token_data["expires_in"],
                    'token_created_at': int(time.time()),
                    'usuario_local': True if usuario_local else False
                })

                # Se não existe usuário local, redireciona para completar cadastro
                if not usuario_local:
                    return redirect('completar_cadastro')

            except Exception as e:
                logger.error(f"Erro ao decodificar token: {str(e)}")
                if hasattr(e, '__cause__'):
                    logger.error(f"Causa do erro: {e.__cause__}")
                return redirect("home")

            return redirect("home")
        else:
            logger.error(f"Erro ao obter token: {response.json()}")
            return HttpResponse(f"Erro ao obter token: {response.json()}", status=400)
    except Exception as e:
        logger.error(f"Erro no callback SSO: {str(e)}")
        return HttpResponse("Erro interno do servidor", status=500)

# Rota para logout


def logout_sso(request):
    request.session.flush()
    return redirect("home")


def ajax_instituicao(request):
    try:
        categoria_instituicao = request.GET.get('categoria_instituicao')
        query = request.GET.get('term', '')

        instituicoes = Instituicao.objects.filter(
            categoria_instituicao=categoria_instituicao)[:10]
        if query:
            instituicoes = Instituicao.objects.filter(
                categoria_instituicao=categoria_instituicao,
                instituicao__icontains=query
            )[:10]

        results = [{'id': inst.id, 'text': inst.instituicao}
                   for inst in instituicoes]
        logger.info(
            f"Busca de instituições realizada - Categoria: {categoria_instituicao}, Query: {query}")
        return JsonResponse({'results': results})
    except Exception as e:
        logger.error(f"Erro na busca de instituições: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def ajax_cargo(request):
    try:
        categoria_instituicao = request.GET.get('categoria_instituicao')
        query = request.GET.get('term', '')

        cargos = Cargo.objects.filter(
            categoria_instituicao=categoria_instituicao)[:10]
        if query:
            cargos = Cargo.objects.filter(
                categoria_instituicao=categoria_instituicao,
                cargo__icontains=query
            )[:10]

        results = [{'id': cargo.id, 'text': cargo.cargo} for cargo in cargos]
        logger.info(
            f"Busca de cargos realizada - Categoria: {categoria_instituicao}, Query: {query}")
        return JsonResponse({'results': results})
    except Exception as e:
        logger.error(f"Erro na busca de cargos: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def ajax_cidade(request):
    try:
        sigla_uf = request.GET.get('sigla_uf')
        query = request.GET.get('term', '')

        cidades = Cidades.objects.filter(sigla_uf=sigla_uf)[:10]
        if query:
            cidades = Cidades.objects.filter(
                sigla_uf=sigla_uf, cidade__icontains=query)[:10]

        results = [{'id': cidade.id, 'text': cidade.cidade}
                   for cidade in cidades]
        logger.info(
            f"Busca de cidades realizada - UF: {sigla_uf}, Query: {query}")
        return JsonResponse({'results': results})
    except Exception as e:
        logger.error(f"Erro na busca de cidades: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def ajax_usuarios(request):
    try:
        query = request.GET.get('term', '')
        query = query.strip()

        usuarios = CustomUser.objects.filter(
            Q(nome_completo__icontains=query)
        )[:10]

        results = [{'id': user.cpf, 'text': user.nome_completo}
                   for user in usuarios]
        logger.info(f"Busca de usuários realizada - Query: {query}")
        return JsonResponse({'results': results})
    except Exception as e:
        logger.error(f"Erro na busca de usuários: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def completar_cadastro(request):
    try:
        usuario_cpf = int(request.session.get('cpf'))
        if not usuario_cpf:
            logger.warning(
                "Tentativa de acesso ao completar cadastro sem CPF na sessão")
            messages.error(request, "Sessão inválida ou expirada.")
            return redirect('login')

        try:
            usuario_data = CustomUser.objects.get(cpf=usuario_cpf)
            is_new_user = False
            logger.info(f"Usuário existente encontrado: {usuario_cpf}")
        except CustomUser.DoesNotExist:
            is_new_user = True
            usuario_data = CustomUser(
                cpf=usuario_cpf,
                nome_completo=request.session.get('nome_completo'),
                email=request.session.get('email')
            )
            logger.info(f"Preparando novo usuário: {usuario_cpf}")

        if request.method == 'POST':
            try:
                with transaction.atomic():
                    instituicao = Instituicao.objects.get(id=request.POST.get(
                        'instituicao')) if request.POST.get('instituicao') else None
                    cargo = Cargo.objects.get(id=request.POST.get(
                        'cargo')) if request.POST.get('cargo') else None
                    cidade = Cidades.objects.get(id=request.POST.get(
                        'cidade')) if request.POST.get('cidade') else None
                    uf_residencia = request.POST.get('uf')

                    usuario_data.telefone = ''.join(c for c in request.POST.get(
                        'telefone', '') if c.isdigit()) or None
                    usuario_data.instituicao = instituicao
                    usuario_data.cargo = cargo
                    usuario_data.cidade = cidade
                    usuario_data.uf_residencia = uf_residencia

                    usuario_data.save()
                    logger.info(
                        f"{'Novo usuário criado' if is_new_user else 'Usuário atualizado'}: {usuario_cpf}")

                    messages.success(
                        request, 'Cadastro concluído com sucesso!' if is_new_user else 'Usuário atualizado com sucesso!')
                    return redirect('home')

            except Exception as e:
                logger.error(f"Erro ao salvar cadastro: {str(e)}")
                messages.error(request, f'Erro ao salvar cadastro: {str(e)}')

        context = {
            'usuario': usuario_data,
            'instituicoes': Instituicao.objects.all(),
            'cargos': Cargo.objects.all(),
            'cidades': Cidades.objects.all(),
            'categorias_instituicao': CategoriaInstituicao.objects.all(),
            'choice_ufs': UFs.objects.all().order_by('uf'),
            'is_new_user': is_new_user
        }

        return render(request, 'auth/completa-cadastro.html', context)

    except Exception as e:
        logger.error(f"Erro no completar cadastro: {str(e)}")
        messages.error(request, "Erro ao processar cadastro.")
        return redirect('login')


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser)
def logs(request):
    page = request.GET.get('page', 1)
    usuario_cpf = request.GET.get('usuario')
    rota = request.GET.get('rota')
    ip = request.GET.get('ip')
    data_inicial = request.GET.get('data_inicial')
    data_final = request.GET.get('data_final')

    logs = UserLogs.objects.all().order_by('-created_at')

    if usuario_cpf:
        logs = logs.filter(usuario__cpf=usuario_cpf)

    if rota:
        logs = logs.filter(log__icontains=rota)

    if ip:
        logs = logs.filter(ip=ip)

    if data_inicial:
        logs = logs.filter(created_at__date__gte=data_inicial)

    if data_final:
        logs = logs.filter(created_at__date__lte=data_final)

    usuarios = CustomUser.objects.all()

    paginator = Paginator(logs, 10)  # 10 logs por página

    try:
        logs_paginados = paginator.page(page)
    except:
        logs_paginados = paginator.page(1)

    return render(request, 'admin/logs.html', {
        'logs': logs_paginados,
        'paginator': paginator,
        'usuarios': usuarios
    })


@login_required(login_url='/login')
def dados_usuario(request):
    try:
        if request.method == 'POST':
            try:
                with transaction.atomic():
                    instituicao = Instituicao.objects.get(id=request.POST.get(
                        'instituicao')) if request.POST.get('instituicao') else None
                    cargo = Cargo.objects.get(id=request.POST.get(
                        'cargo')) if request.POST.get('cargo') else None
                    cidade = Cidades.objects.get(id=request.POST.get(
                        'cidade')) if request.POST.get('cidade') else None
                    uf_residencia = request.POST.get('uf')

                    request.user.telefone = ''.join(c for c in request.POST.get(
                        'telefone', '') if c.isdigit()) or None
                    request.user.instituicao = instituicao
                    request.user.cargo = cargo
                    request.user.cidade = cidade
                    request.user.uf_residencia = uf_residencia

                    request.user.save()
                    logger.info(
                        f"Dados do usuário atualizados: {request.user.cpf}")

                    messages.success(request, 'Dados atualizados com sucesso!')
                    return redirect('dados_usuario')

            except Exception as e:
                logger.error(f"Erro ao atualizar dados: {str(e)}")
                messages.error(request, f'Erro ao atualizar dados: {str(e)}')

        context = {
            'usuario': request.user,
            'choice_ufs': UFs.objects.all().order_by('uf'),
            'categorias_instituicao': CategoriaInstituicao.objects.all()
        }

        return render(request, 'auth/completa-cadastro.html', context)

    except Exception as e:
        logger.error(f"Erro ao acessar dados do usuário: {str(e)}")
        messages.error(request, "Erro ao carregar seus dados.")
        return redirect('home')


##############################################################################################################################################
# UNIDADES
##############################################################################################################################################

@login_required
def unidade_list(request):
    unidades = Unidade.objects.all().select_related('instituicao', 'parent')
    return render(request, 'user/unidade/list.html', {'unidades': unidades})


@login_required
def unidade_create(request):
    if request.method == 'POST':
        form = UnidadeForm(request.POST)
        if form.is_valid():
            unidade = form.save(commit=False)
            unidade.created_by = request.user
            unidade.updated_by = request.user
            unidade.save()
            messages.success(request, 'Unidade criada com sucesso!')
            return redirect('unidade_list')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = UnidadeForm()

    return render(request, 'user/unidade/form.html', {
        'form': form,
        'title': 'Nova Unidade',
        'button_text': 'Criar Unidade',
        'unidades': Unidade.objects.all().select_related('instituicao', 'parent')
    })


@login_required
def unidade_update(request, pk):
    unidade = get_object_or_404(Unidade, pk=pk)

    if request.method == 'POST':
        form = UnidadeForm(request.POST, instance=unidade)
        if form.is_valid():
            unidade = form.save(commit=False)
            unidade.updated_by = request.user
            unidade.save()
            messages.success(request, 'Unidade atualizada com sucesso!')
            return redirect('unidade_list')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = UnidadeForm(instance=unidade)

    return render(request, 'user/unidade/form.html', {
        'form': form,
        'unidade': unidade,
        'title': 'Editar Unidade',
        'button_text': 'Atualizar Unidade',
        'unidades': Unidade.objects.all().select_related('instituicao', 'parent').exclude(id=unidade.id),
    })


@login_required
def unidade_delete(request, pk):
    unidade = get_object_or_404(Unidade, pk=pk)

    if request.method == 'POST':
        unidade.delete()
        messages.success(request, 'Unidade excluída com sucesso!')
        return redirect('unidade_list')

    return render(request, 'user/unidade/delete.html', {'unidade': unidade})


@login_required
def unidade_detail(request, pk):
    unidade = get_object_or_404(Unidade, pk=pk)

    unidade_pai = Unidade.objects.filter(id=unidade.parent_id)
    unidades_vinculadas = Unidade.objects.filter(parent=unidade)

    return render(request, 'user/unidade/detail.html', {'unidade': unidade, 'unidade_pai': unidade_pai, 'unidades_vinculadas': unidades_vinculadas})


##############################################################################################################################################
# CRUD DE USUÁRIOS
##############################################################################################################################################

@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser)
def usuario_list(request):
    usuarios = CustomUser.objects.all().order_by('nome_completo')
    return render(request, 'user/usuarios/list.html', {'usuarios': usuarios})


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser)
def usuario_create(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, 'Usuário criado com sucesso!')
            return redirect('usuario_list')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = UsuarioForm()

    return render(request, 'user/usuarios/form.html', {
        'form': form,
        'title': 'Novo Usuário',
        'button_text': 'Criar Usuário'
    })


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser)
def usuario_detail(request, cpf):
    usuario = get_object_or_404(CustomUser, cpf=cpf)
    return render(request, 'user/usuarios/detail.html', {'usuario': usuario})


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser)
def usuario_edit(request, cpf):
    print(f"[DEBUG] usuario_edit - CPF recebido na URL: {cpf}")
    usuario = get_object_or_404(CustomUser, cpf=cpf)
    print(f"[DEBUG] usuario_edit - Usuário encontrado: {usuario}")
    print(f"[DEBUG] usuario_edit - CPF do usuário: {usuario.cpf}")
    
    if request.method == 'POST':
        print(f"[DEBUG] usuario_edit - Método POST")
        print(f"[DEBUG] usuario_edit - POST data: {request.POST}")
        print(f"[DEBUG] usuario_edit - CPF no POST: {request.POST.get('cpf')}")
        
        form = UsuarioForm(request.POST, instance=usuario)
        print(f"[DEBUG] usuario_edit - Form criado")
        
        if form.is_valid():
            print(f"[DEBUG] usuario_edit - Form é válido, salvando...")
            form.save()
            messages.success(request, 'Usuário atualizado com sucesso!')
            return redirect('usuario_list')
        else:
            print(f"[DEBUG] usuario_edit - Form inválido")
            print(f"[DEBUG] usuario_edit - Erros do form: {form.errors}")
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        print(f"[DEBUG] usuario_edit - Método GET")
        form = UsuarioForm(instance=usuario)

    return render(request, 'user/usuarios/form.html', {
        'form': form,
        'title': f'Editar Usuário: {usuario.nome_completo}',
        'button_text': 'Atualizar Usuário'
    })


@login_required(login_url='/login')
@user_passes_test(lambda u: u.is_superuser)
def usuario_delete(request, cpf):
    usuario = get_object_or_404(CustomUser, cpf=cpf)
    try:
        usuario.delete()
        messages.success(request, 'Usuário excluído com sucesso!')
    except Exception as e:
        messages.error(request, 'Não foi possível excluir o usuário.')
    return redirect('usuario_list')
