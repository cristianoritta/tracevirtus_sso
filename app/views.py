from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import logging
from .models import Caso, Investigado, CasoInvestigado, Relatorio
from financeira.models import RIF, Comunicacao, Envolvido, InformacaoAdicional, Ocorrencia
from .forms import CasoForm, InvestigadoForm, AdicionarInvestigadoForm
from django.utils import timezone
from .forms import RelatorioForm

logger = logging.getLogger(__name__)

# As rotas de login foram movidas para user/views.py


@login_required(login_url='/login')
def home(request):
    casos = Caso.objects.filter(created_by=request.user)
    caso_ativo = casos.filter(ativo=True).first()
    
    volume_financeiro_por_comunicacao = {}
    volume_financeiro_bancaria = {}
    
    if caso_ativo:
        # RIF: Calcular o volume financeiro por comunicação
        for comunicacao in caso_ativo.comunicacao_set.all():
            volume_financeiro_por_comunicacao[f"{comunicacao.rif} - Ind. {comunicacao.indexador}"] = comunicacao.campo_a
        
    return render(request, 'home/index.html', {'caso': caso_ativo, 'casos': casos, 'volume_financeiro_por_comunicacao': volume_financeiro_por_comunicacao})


@login_required(login_url='/login')
def casos(request):
    casos = Caso.objects.all()
    return render(request, 'casos/index.html', {'casos': casos})


@login_required(login_url='/login')
def novo_caso(request):
    if request.method == 'POST':
        form = CasoForm(request.POST)
        if form.is_valid():
            caso = form.save(commit=False)
            caso.created_by = request.user
            caso.save()
            messages.success(request, 'Caso criado com sucesso!')
            return redirect('casos')
        else:
            messages.error(request, 'Erro ao criar caso. Verifique os dados.')
    else:
        form = CasoForm()

    return render(request, 'casos/novo.html', {'form': form})


@login_required(login_url='/login')
def editar_caso(request, id):
    caso = get_object_or_404(Caso, id=id, created_by=request.user)
    if request.method == 'POST':
        form = CasoForm(request.POST, instance=caso)
        if form.is_valid():
            form.save()
            messages.success(request, 'Caso atualizado com sucesso!')
            return redirect('casos')
        else:
            messages.error(
                request, 'Erro ao atualizar caso. Verifique os dados.')
    else:
        form = CasoForm(instance=caso)

    return render(request, 'casos/novo.html', {'form': form})


@login_required(login_url='/login')
def excluir_caso(request, id):
    caso = get_object_or_404(Caso, id=id, created_by=request.user)
    
    if request.method == 'POST':
        # O Django já vai cuidar de excluir todos os registros relacionados
        # devido ao on_delete=models.CASCADE nas ForeignKeys
        caso.delete()
        messages.success(request, 'Caso excluído com sucesso!')
        return redirect('casos')
    
    return render(request, 'casos/excluir.html', {'caso': caso})
    caso.delete()
    messages.success(request, 'Caso excluído com sucesso!')
    return redirect('casos')


@login_required(login_url='/login')
def caso_ativo(request, id):
    caso = get_object_or_404(Caso, id=id, created_by=request.user)
    caso.ativo = not caso.ativo
    caso.save()
    return redirect('casos')


@login_required(login_url='/login')
def investigados(request, id):
    caso = get_object_or_404(Caso, id=id, created_by=request.user)
    investigados = caso.investigados.all()  # Agora funciona com o related_name
    return render(request, 'casos/investigados.html', {
        'caso': caso,
        'investigados': investigados
    })


@login_required(login_url='/login')
def adicionar_investigado(request, caso_id):
    caso = get_object_or_404(Caso, id=caso_id, created_by=request.user)

    if request.method == 'POST':
        # Verificar se é busca de investigado existente ou criação de novo
        if 'buscar_existente' in request.POST:
            form = AdicionarInvestigadoForm(request.POST)
            if form.is_valid():
                cpf_cnpj = form.cleaned_data['cpf_cnpj_existente']
                try:
                    investigado = Investigado.objects.get(cpf_cnpj=cpf_cnpj)
                    # Verificar se já não está associado ao caso
                    if not CasoInvestigado.objects.filter(caso=caso, investigado=investigado).exists():
                        CasoInvestigado.objects.create(
                            caso=caso,
                            investigado=investigado,
                            observacoes=form.cleaned_data['observacoes']
                        )
                        messages.success(
                            request, f'Investigado {investigado.nome} adicionado ao caso com sucesso!')
                        return redirect('investigados', id=caso_id)
                    else:
                        messages.warning(
                            request, 'Este investigado já está associado ao caso.')
                except Investigado.DoesNotExist:
                    messages.error(
                        request, 'Investigado não encontrado com este CPF/CNPJ.')

        elif 'criar_novo' in request.POST:
            investigado_form = InvestigadoForm(request.POST)
            adicionar_form = AdicionarInvestigadoForm(request.POST)

            if investigado_form.is_valid() and adicionar_form.is_valid():
                try:
                    investigado = investigado_form.save()
                    CasoInvestigado.objects.create(
                        caso=caso,
                        investigado=investigado,
                        observacoes=adicionar_form.cleaned_data['observacoes']
                    )
                    messages.success(
                        request, f'Investigado {investigado.nome} criado e adicionado ao caso com sucesso!')
                    return redirect('investigados', id=caso_id)
                except Exception as e:
                    messages.error(
                        request, f'Erro ao criar investigado: {str(e)}')
    else:
        investigado_form = InvestigadoForm()
        adicionar_form = AdicionarInvestigadoForm()

    return render(request, 'casos/adicionar_investigado.html', {
        'caso': caso,
        'investigado_form': investigado_form,
        'adicionar_form': adicionar_form
    })


@login_required(login_url='/login')
def buscar_investigado(request):
    """AJAX endpoint para buscar investigado por CPF/CNPJ"""
    if request.method == 'GET':
        cpf_cnpj = request.GET.get('cpf_cnpj', '')
        if cpf_cnpj:
            try:
                investigado = Investigado.objects.get(cpf_cnpj=cpf_cnpj)
                return JsonResponse({
                    'found': True,
                    'nome': investigado.nome,
                    'tipo': investigado.get_tipo_display(),
                    'dados_pessoais': investigado.dados_pessoais,
                })
            except Investigado.DoesNotExist:
                return JsonResponse({'found': False})
    return JsonResponse({'found': False})


@login_required(login_url='/login')
def editar_investigado(request, caso_id, investigado_id):
    caso = get_object_or_404(Caso, id=caso_id, created_by=request.user)
    caso_investigado = get_object_or_404(
        CasoInvestigado, caso=caso, investigado_id=investigado_id)

    if request.method == 'POST':
        form = InvestigadoForm(
            request.POST, instance=caso_investigado.investigado)
        if form.is_valid():
            form.save()
            # Atualizar observações específicas do caso se fornecidas
            observacoes = request.POST.get('observacoes_caso', '')
            if observacoes:
                caso_investigado.observacoes = observacoes
                caso_investigado.save()

            messages.success(request, 'Investigado atualizado com sucesso!')
            return redirect('investigados', id=caso_id)
        else:
            messages.error(
                request, 'Erro ao atualizar investigado. Verifique os dados.')
    else:
        form = InvestigadoForm(instance=caso_investigado.investigado)

    return render(request, 'casos/editar_investigado.html', {
        'caso': caso,
        'investigado': caso_investigado.investigado,
        'caso_investigado': caso_investigado,
        'form': form
    })


@login_required(login_url='/login')
def remover_investigado(request, caso_id, investigado_id):
    caso = get_object_or_404(Caso, id=caso_id, created_by=request.user)
    caso_investigado = get_object_or_404(
        CasoInvestigado, caso=caso, investigado_id=investigado_id)

    investigado_nome = caso_investigado.investigado.nome

    if request.method == 'DELETE':
        # Requisição HTMX
        caso_investigado.delete()

        # Retornar resposta vazia com header de sucesso para HTMX
        response = HttpResponse('')
        response['X-Success-Message'] = f'Investigado {investigado_nome} removido do caso com sucesso!'
        return response

    elif request.method == 'POST':
        # Requisição tradicional de formulário
        caso_investigado.delete()
        messages.success(
            request, f'Investigado {investigado_nome} removido do caso com sucesso!')
        return redirect('investigados', id=caso_id)

    # GET request - não permitido
    return HttpResponse(status=405)


@login_required(login_url='/login')
def detalhes_investigado(request, caso_id, investigado_id):
    """View para carregar detalhes do investigado no modal"""
    caso = get_object_or_404(Caso, id=caso_id, created_by=request.user)
    caso_investigado = get_object_or_404(
        CasoInvestigado, caso=caso, investigado_id=investigado_id)

    # Calcular estatísticas
    investigado = caso_investigado.investigado
    casos_relacionados = CasoInvestigado.objects.filter(
        investigado=investigado)
    total_casos = casos_relacionados.count()
    casos_ativos = casos_relacionados.filter(caso__ativo=True).count()
    casos_andamento = casos_relacionados.filter(
        caso__status='andamento').count()

    return render(request, 'casos/partials/modal_detalhes_investigado.html', {
        'caso': caso,
        'investigado': investigado,
        'caso_investigado': caso_investigado,
        'estatisticas': {
            'total_casos': total_casos,
            'casos_ativos': casos_ativos,
            'casos_andamento': casos_andamento,
        }
    })


@login_required(login_url='/login')
@require_POST
def excluir_investigado(request, investigado_id):
    """Exclui completamente um investigado do sistema"""
    investigado = get_object_or_404(Investigado, id=investigado_id)

    # Verificar se o investigado está associado a algum caso
    if CasoInvestigado.objects.filter(investigado=investigado).exists():
        messages.error(
            request, 'Não é possível excluir este investigado pois ele está associado a casos. Remova-o dos casos primeiro.')
        return redirect('investigados', id=request.POST.get('caso_id', 1))

    investigado_nome = investigado.nome
    investigado.delete()

    messages.success(
        request, f'Investigado {investigado_nome} excluído permanentemente do sistema!')
    return redirect('investigados', id=request.POST.get('caso_id', 1))


########################################################################
#
# CRUD DE RELATÓRIOS
#
########################################################################

@login_required
def relatorios_list(request):
    """Lista todos os relatórios"""
    relatorios = Relatorio.objects.all().order_by('-created_at')
    context = {
        'relatorios': relatorios,
        'title': 'Relatórios'
    }
    return render(request, 'relatorios/list.html', context)

@login_required
def relatorio_create(request):
    """Cria um novo relatório"""
    if request.method == 'POST':
        form = RelatorioForm(request.POST, request.FILES)
        if form.is_valid():
            relatorio = form.save(commit=False)
            relatorio.created_by = request.user
            relatorio.historico_atualizacoes = {
                'atualizacoes': [
                    {
                        'data': timezone.now().isoformat(),
                        'usuario': request.user.username,
                        'acao': 'Criação do relatório',
                        'descricao': f'Relatório "{relatorio.nome}" criado'
                    }
                ]
            }
            relatorio.save()
            messages.success(request, 'Relatório criado com sucesso!')
            return redirect('/relatorios')
    else:
        form = RelatorioForm()
    
    context = {
        'form': form,
        'title': 'Criar Relatório',
        'action': 'create'
    }
    return render(request, 'relatorios/form.html', context)

@login_required
def relatorio_detail(request, pk):
    """Exibe os detalhes de um relatório"""
    relatorio = get_object_or_404(Relatorio, pk=pk)
    context = {
        'relatorio': relatorio,
        'title': f'Detalhes - {relatorio.nome}'
    }
    return render(request, 'relatorios/detail.html', context)

@login_required
def relatorio_update(request, pk):
    """Atualiza um relatório existente"""
    relatorio = get_object_or_404(Relatorio, pk=pk)
    
    if request.method == 'POST':
        form = RelatorioForm(request.POST, request.FILES, instance=relatorio)
        if form.is_valid():
            # Adiciona entrada no histórico
            historico = relatorio.historico_atualizacoes
            if not historico:
                historico = {'atualizacoes': []}
            
            historico['atualizacoes'].append({
                'data': timezone.now().isoformat(),
                'usuario': request.user.username,
                'acao': 'Atualização do relatório',
                'descricao': f'Relatório "{relatorio.nome}" atualizado'
            })
            
            relatorio = form.save(commit=False)
            relatorio.historico_atualizacoes = historico
            relatorio.save()
            
            messages.success(request, 'Relatório atualizado com sucesso!')
            return redirect('relatorio_detail', pk=relatorio.pk)
    else:
        form = RelatorioForm(instance=relatorio)
    
    context = {
        'form': form,
        'relatorio': relatorio,
        'title': f'Editar - {relatorio.nome}',
        'action': 'update'
    }
    return render(request, 'relatorios/form.html', context)

@login_required
def relatorio_delete(request, pk):
    """Remove um relatório"""
    relatorio = get_object_or_404(Relatorio, pk=pk)
    
    if request.method == 'POST':
        nome = relatorio.nome
        relatorio.delete()
        messages.success(request, f'Relatório "{nome}" removido com sucesso!')
        return redirect('relatorios_list')
    
    context = {
        'relatorio': relatorio,
        'title': f'Remover - {relatorio.nome}'
    }
    return render(request, 'relatorios/delete.html', context)

@login_required
def relatorio_download(request, pk):
    """Faz download do arquivo do relatório"""
    relatorio = get_object_or_404(Relatorio, pk=pk)
    
    if relatorio.arquivo:
        response = HttpResponse(relatorio.arquivo, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{relatorio.arquivo.name}"'
        return response
    else:
        messages.error(request, 'Arquivo não encontrado!')
        return redirect('relatorio_detail', pk=pk)

def relatorio_documentacao(request):
    """Exibe a documentação de dados dos relatórios"""
    
    return render(request, 'relatorios/documentacao.html')