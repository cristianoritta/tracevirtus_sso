from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from unidecode import unidecode
from django.utils import timezone
import json
from .models import RIF, Comunicacao, Envolvido, Ocorrencia, InformacaoAdicional, KYC, AnaliseIA, Prompt
from app.models import Caso, Arquivo, Relatorio
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
import pandas as pd
import sqlite3
import os
import tempfile
import locale
from django.db import connection
from django.views.decorators.csrf import csrf_exempt
from app.functions import sha256_dataframe
from utils.ia import executar_prompt
from django.views.decorators.http import require_GET
from docxtpl import DocxTemplate
from docx import Document
import zipfile
from io import BytesIO
from utils.moeda import moeda, processar_valor_monetario
from utils.cpfcnpj import validar_e_limpar_cpf_cnpj
from utils.formatar_nomes import normalizar_nome
import json
from .models import Prompt
import time
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)
pd.options.mode.chained_assignment = None

#########################################################################################################################
# FUNÇÕES DE APOIO
#########################################################################################################################


def _buscar_caso_ativo(request: 'Request') -> 'Caso':
    """Busca o caso ativo a partir da sessão do usuário.

    Esta função verifica se há um caso ativo na sessão do usuário.
    Se não houver, busca o primeiro caso ativo disponível.

    Args:
        request (Request): Requisição HTTP atual.

    Returns:
        Caso: Instância do caso ativo.
    """
    # Busca o caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    
    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')

    return caso_ativo


def _buscar_titular_ocorrencia(ocorrencia: 'Ocorrencia') -> Optional['Envolvido']:
    """Busca o titular associado a uma ocorrência específica.

    Função auxiliar que localiza o envolvido marcado como 'Titular' 
    relacionado à ocorrência fornecida, usando caso_id e indexador
    como critérios de busca.

    Args:
        ocorrencia (Ocorrencia): Instância da ocorrência para buscar o titular.

    Returns:
        Optional[Envolvido]: Instância do titular se encontrado, None caso contrário.
            Se múltiplos titulares existirem, retorna o primeiro encontrado.

    Note:
        Utiliza .first() para evitar MultipleObjectsReturned exception
        e garantir que sempre retorne no máximo um objeto.
    """
    try:
        titular = Envolvido.objects.filter(
            caso_id=ocorrencia.caso_id,
            tipo_envolvido='Titular',
            indexador=ocorrencia.indexador
        ).first()

        return titular

    except Exception as e:
        logger.warning(
            "Erro ao buscar titular para ocorrência %s: %s",
            ocorrencia.id,
            str(e)
        )
        return None


def _get_prompt_from_db(modulo, funcao, label=None):
    """Busca um prompt ativo do banco de dados com base no módulo e função.

    Esta função procura um prompt personalizado ativo no banco de dados
    baseado nos parâmetros fornecidos.

    Args:
        modulo (str): Módulo do sistema que utilizará o prompt.
        funcao (str): Função específica que utilizará o prompt.
        label (Optional[str]): Rótulo opcional para identificar o prompt.

    Returns:
        Optional[str]: Texto do prompt se encontrado, None caso contrário.

    Raises:
        Exception: Se houver erro ao consultar o banco de dados.

    Note:
        - Retorna apenas prompts ativos (is_active=True)
        - Se label fornecido, filtra também por label
        - Retorna o primeiro prompt encontrado
    """

    # Busca o prompt no banco de dados
    try:
        if label:
            prompt = Prompt.objects.filter(
                modulo=modulo,
                funcao=funcao,
                label=label,
                is_active=True
            ).first()
        else:
            prompt = Prompt.objects.filter(
                modulo=modulo,
                funcao=funcao,
                is_active=True
            ).first()

        return prompt.prompt if prompt else None
    except Exception as e:
        print(f"Erro ao buscar prompt: {e}")
        return None


def _save_prompt_to_db(request, modulo, funcao, label, prompt_text):
    """Salva um novo prompt no banco de dados.

    Esta função cria um novo registro de prompt no banco de dados
    com os parâmetros fornecidos.

    Args:
        modulo (str): Módulo do sistema que utilizará o prompt
        funcao (str): Função específica que utilizará o prompt
        label (str): Rótulo para identificar o prompt
        prompt_text (str): Texto do prompt a ser salvo

    Returns:
        None

    Raises:
        Exception: Se houver erro ao salvar no banco de dados
    """
    try:
        # Cria novo prompt ativo
        Prompt.objects.create(
            modulo=modulo,
            funcao=funcao,
            label=label,
            prompt=prompt_text,
            is_active=True,
            created_by=request.user
        )

        print(f"Prompt salvo: {prompt_text}")
    except Exception as e:
        print(f"Erro ao salvar prompt: {e}")


def replace_ignorando_acentos(texto, busca, substituto_func):
    """
    Substitui texto ignorando acentuação e maiúsculas/minúsculas.

    Esta função realiza substituição de texto ignorando acentos e diferenças
    entre maiúsculas e minúsculas.

    Args:
        texto (str): Texto onde será feita a substituição
        busca (str): Texto a ser buscado
        substituto_func (callable): Função que retorna o texto substituto

    Returns:
        str: Texto com as substituições realizadas

    Raises:
        None
    """
    # Mapeamento de caracteres com acentos
    mapa_acentos = {
        'a': '[aáàãâä]', 'e': '[eéèêë]', 'i': '[iíìîï]',
        'o': '[oóòõôö]', 'u': '[uúùûü]', 'c': '[cç]', 'n': '[nñ]'
    }

    padrao = ""
    for char in busca.lower():
        if char in mapa_acentos:
            padrao += mapa_acentos[char]
        else:
            padrao += re.escape(char)

    return re.sub(padrao, substituto_func, texto, flags=re.IGNORECASE)


#########################################################################################################################
#
# INDEX
#
#########################################################################################################################
@login_required
def financeira_index(request):

    # Testa se tem um caso ativo.
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre ou ative um caso para continuar.')
        return redirect('casos')

    # Calcular estatísticas
    rifs = RIF.objects.filter(caso=caso_ativo).select_related(
        'caso').order_by('-created_at')
    # Incluir em rif o numero de comunicacoes e envolvidos de cada rif
    for rif in rifs:
        rif.total_comunicacoes = Comunicacao.objects.filter(rif=rif).count()
        rif.total_envolvidos = Envolvido.objects.filter(rif=rif).count()

    total_rifs = rifs.count()
    total_comunicacoes = Comunicacao.objects.filter(caso=caso_ativo).count()
    total_envolvidos = Envolvido.objects.filter(caso=caso_ativo).count()
    total_ocorrencias = Ocorrencia.objects.filter(caso=caso_ativo).count()

    # Dados dos últimos 30 dias
    comunicacoes = Comunicacao.objects.filter(caso=caso_ativo).count()

    comunicacoes = Comunicacao.objects.filter(caso_id=caso_ativo.id)

    # Converte os valores para float
    somas = {
        'total_a': 0,
        'total_b': 0,
        'total_c': 0
    }

    # Lista para armazenar os valores do campo_a para o gráfico
    valores_campo_a = []

    # Dicionário para armazenar os valores por titular
    valores_por_titular = {}

    for comunicacao in comunicacoes:
        try:
            # Remove o símbolo da moeda e espaços
            valor_a = str(comunicacao.campo_a)
            valor_b = str(comunicacao.campo_b)
            valor_c = str(comunicacao.campo_c)
            
            # Converte do formato brasileiro para float
            comunicacao.campo_a = float(valor_a)
            comunicacao.campo_b = float(valor_b)
            comunicacao.campo_c = float(valor_c)

            # Adiciona o valor do campo_a à lista para o gráfico
            valores_campo_a.append(comunicacao.campo_a)

            somas['total_a'] += comunicacao.campo_a
            somas['total_b'] += comunicacao.campo_b
            somas['total_c'] += comunicacao.campo_c

            # Adiciona o valor ao titular correspondente
            titular = Envolvido.objects.filter(
                indexador=comunicacao.indexador, tipo_envolvido='Titular').first()
            if titular:
                if titular.nome_envolvido not in valores_por_titular:
                    valores_por_titular[titular.nome_envolvido] = 0
                valores_por_titular[titular.nome_envolvido] += comunicacao.campo_a

        except (ValueError, AttributeError):
            # Se houver erro na conversão, define como 0
            comunicacao.campo_a = 0
            comunicacao.campo_b = 0
            comunicacao.campo_c = 0
            valores_campo_a.append(0)

    # Somas
    somas['total_a'] = moeda(somas['total_a'])
    somas['total_b'] = moeda(somas['total_b'])
    somas['total_c'] = moeda(somas['total_c'])

    # Converte o dicionário de valores por titular para uma lista de objetos
    valores_por_titular_list = [
        {'titular': k, 'valor': float(v)} for k, v in valores_por_titular.items()
    ]

    # Calcular o volume financeiro por comunicação
    volume_financeiro_por_comunicacao = {}
    for comunicacao in caso_ativo.comunicacao_set.all():
        volume_financeiro_por_comunicacao[f"{comunicacao.rif} - Ind. {comunicacao.indexador}"] = comunicacao.campo_a

    context = {
        'total_rifs': total_rifs,
        'total_comunicacoes': total_comunicacoes,
        'total_envolvidos': total_envolvidos,
        'total_ocorrencias': total_ocorrencias,
        'rifs': rifs,
        'somas': somas,
        'valores_campo_a': valores_campo_a,  # Adiciona os valores para o gráfico
        # Serializa para JSON
        'valores_por_titular': json.dumps(valores_por_titular_list),
        'volume_financeiro_por_comunicacao': json.dumps(volume_financeiro_por_comunicacao),
    }

    return render(request, 'financeira/index.html', context)


#########################################################################################################################
# CADASTRO DE RIF
#########################################################################################################################
@login_required
#@csrf_exempt
def cadastrar_rif(request):
    if request.method == 'POST':
        try:
            numero = request.POST.get('numero')
            outras_informacoes = request.POST.get('outras_informacoes')

            # Buscar caso ativo
            caso_ativo = Caso.objects.filter(ativo=True).first()
            if not caso_ativo:
                return JsonResponse({
                    'success': False,
                    'message': 'Nenhum caso ativo encontrado.'
                }, status=400)

            # Validar se número já existe
            if RIF.objects.filter(numero=numero, caso=caso_ativo).exists():
                return JsonResponse({
                    'success': False,
                    'errors': {'numero': ['Já existe uma RIF cadastrada com este número.']},
                    'message': 'Já existe uma RIF cadastrada com este número.'
                }, status=400)

            # Criar nova RIF associada ao caso ativo
            rif = RIF.objects.create(
                numero=numero,
                outras_informacoes=outras_informacoes or '',
                caso=caso_ativo
            )

            return JsonResponse({
                'success': True,
                'message': 'RIF cadastrada com sucesso!',
                'data': {
                    'id': rif.id,
                    'numero': rif.numero
                }
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': 'Erro ao cadastrar RIF. Tente novamente.',
                'error': str(e)
            }, status=500)

    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)


#########################################################################################################################
# EXCLUIR RIF
#########################################################################################################################
@login_required
#@csrf_exempt
def excluir_rif(request, rif_id):
    rif = RIF.objects.get(id=rif_id)

    # Excluir os arquivos associados à RIF
    Arquivo.objects.filter(caso_id=rif.caso_id, external_id=rif.id).delete()
    # Excluir as comunicações associadas à RIF
    Comunicacao.objects.filter(caso_id=rif.caso_id, rif_id=rif.id).delete()
    # Excluir os envolvidos associados à RIF
    Envolvido.objects.filter(caso_id=rif.caso_id, rif_id=rif.id).delete()
    # Excluir as ocorrências associadas à RIF
    Ocorrencia.objects.filter(caso_id=rif.caso_id, rif_id=rif.id).delete()

    rif.delete()

    # retorna um json com o sucesso
    return JsonResponse({
        'success': True,
        'message': 'RIF excluída com sucesso!'
    }, status=200)


#########################################################################################################################
# COMUNICAÇÕES - Lista as Comunicações
#########################################################################################################################
@login_required
def financeira_comunicacoes(request):

    caso_ativo = _buscar_caso_ativo(request)

    # Busca todas as comunicações do caso ativo, incluindo o número do RIF
    comunicacoes = Comunicacao.objects.filter(
        caso_id=caso_ativo.id).select_related('rif')

    # Destaca no texto de informações adicionais os nomes dos envolvidos
    envolvidos = Envolvido.objects.filter(
        caso_id=caso_ativo.id).select_related('rif').distinct()

    titulares_distintos = []    
    for comunicacao in comunicacoes:
        texto = comunicacao.informacoes_adicionais
        if texto:
            for envolvido in envolvidos:
                # Pesquisa os nomes sem acentos
                if envolvido.nome_envolvido and unidecode(envolvido.nome_envolvido).upper() in unidecode(texto).upper():
                    def replacer(match):
                        return f'<span style="border-bottom: 2px dotted red;">{match.group()}</span>'

                    texto = replace_ignorando_acentos(
                        texto, envolvido.nome_envolvido, replacer)

            comunicacao.informacoes_adicionais = texto

        titular = _buscar_titular_ocorrencia(comunicacao)
        comunicacao.titular = titular.nome_envolvido
        titulares_distintos.append(titular.nome_envolvido)

    context = {
        'comunicacoes': comunicacoes,
        'comunicacoes_distinct': comunicacoes.values_list('nome_comunicante', flat=True).distinct(),
        'titulares_distintos': envolvidos.values_list('nome_envolvido', flat=True).distinct(),
        'caso': caso_ativo,
        'envolvidos': envolvidos,
    }
    return render(request, 'financeira/comunicacoes.html', context)


@login_required
def financeira_envolvidos(request):
    # Busca o caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')

    # Busca todos os envolvidos do caso ativo, incluindo o número do RIF
    envolvidos = Envolvido.objects.filter(
        caso_id=caso_ativo.id).select_related('rif')

    context = {
        'envolvidos': envolvidos,
        'caso': caso_ativo,
    }
    return render(request, 'financeira/envolvidos.html', context)


########################################################################################
# LISTAR OCORRENCIAS DO CASO ATIVO
########################################################################################
@login_required
def financeira_ocorrencias(request):
    """
    Endpoint para listar as ocorrências do caso ativo

    @param request: Request
    @return: Renderiza a página de ocorrências
    """

    # Busca o caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')

    # Busca todas as ocorrências do caso ativo, incluindo o número do RIF
    ocorrencias = Ocorrencia.objects.filter(
        caso_id=caso_ativo.id).select_related('rif')

    # Adiciona a comunicação correspondente a cada ocorrência
    for ocorrencia in ocorrencias:
        ocorrencia.comunicacao = Comunicacao.objects.filter(
            caso_id=caso_ativo.id,
            rif_id=ocorrencia.rif_id,
            indexador=ocorrencia.indexador).first()

    # Serializar as ocorrências para JSON
    ocorrencias_json = json.dumps([
        {
            'indexador': o.indexador,
            'ocorrencia': o.ocorrencia[:6],
            'id': o.id,
            'rif': {'numero': o.rif.numero},
            'comunicacao': o.comunicacao.id if o.comunicacao else None
        } for o in ocorrencias])

    context = {
        'ocorrencias': ocorrencias,
        'caso': caso_ativo,
        'ocorrencias_json': ocorrencias_json  # Adicionar esta linha
    }
    return render(request, 'financeira/ocorrencias.html', context)


########################################################################################
# AJUDA PARA OCORRENCIA
########################################################################################
@login_required
def ocorrencia_ajuda(request, id):

    # Buscar a ocorrência específica
    ocorrencia = get_object_or_404(Ocorrencia, id=id)

    # Buscar titular associado à ocorrência
    titular = _buscar_titular_ocorrencia(ocorrencia)

    # Recupera a comunicação, para obter o valor do campo_a
    comunicacao = Comunicacao.objects.filter(
        caso_id=ocorrencia.caso_id, indexador=ocorrencia.indexador).first()

    # Buscar prompt do banco de dados
    prompt_text = _get_prompt_from_db(
        'financeira', 'ocorrencia_ajuda', 'Análise de Ocorrência COAF')

    if not prompt_text:
        prompt_text = "Você é um especialista em investigação financeira e lavagem de dinheiro. Explique o que significa na prática, e com exemplos, essas tipificacoes da Lavagem do Dinheiro informadas pelo COAF: {ocorrencia}. O nome do titular é {titular}, o CPF/CNPJ é {cpf_cnpj}, a agência é {agencia} e a conta é {conta} e o valor para lavagem é {valor}."

        # Salvar o prompt no banco de dados
        _save_prompt_to_db(request, 'financeira', 'ocorrencia_ajuda',
                           'Análise de Ocorrência COAF', prompt_text)

    # Executar o prompt com os dados da ocorrência
    ajuda = executar_prompt([{
        "role": "user",
        "content": prompt_text.format(
            ocorrencia=ocorrencia.ocorrencia,
            titular=titular.nome_envolvido if titular else "Não identificado",
            cpf_cnpj=titular.cpf_cnpj_envolvido if titular else "N/A",
            agencia=titular.agencia_envolvido if titular else "N/A",
            conta=titular.conta_envolvido if titular else "N/A",
            valor=comunicacao.campo_a if comunicacao else "R$ 100.000,00"
        )
    }])

    # Retorna a ajuda em formato markdown
    return HttpResponse(ajuda, content_type="text/markdown; charset=utf-8")


########################################################################################
# ABRIR A TELA DE INFORMAÇÕES ADICIONAIS
#
# A cada abertura, processa as informações para buscar novos dados
########################################################################################
@login_required
def financeira_informacoesadicionais(request):

    try:
        # Busca o caso ativo
        caso_ativo = _buscar_caso_ativo(request)

        # Carrega todas as comunicacoes que ainda não tem informacoes_adicionais

        comunicacoes = Comunicacao.objects.filter(caso=caso_ativo, codigo_segmento=41).exclude(
            id__in=InformacaoAdicional.objects.values('comunicacao_id')
        )

        for com in comunicacoes:

            # TODO: Esse processamento, futuramente, será feito em background e em fila
            time.sleep(1)

            # Buscar prompt do banco de dados
            prompt_text = _get_prompt_from_db(
                'financeira', 'informacoes_adicionais', 'Análise de Informações Adicionais')

            if not prompt_text:
                prompt_text = """Você é um analista de transações financeiras. Extraia registros de transações a partir de um texto não com o seguinte padrão. Cada registro pode ter:
                tipo: crédito ou débito (só esses dois valores)
                nome: Nome completo da pessoa ou empresa
                cpf_cnpj: CPF ou CNPJ
                valor: Valor da transação (formato brasileiro: R$ XX,XX)
                quantidade: Quantidade (de eventos)
                plataforma: Plataforma de transação (PIX, Depósito, Transferência, etc.)

                Os dados podem estar separados por pipes (|) e conter artefatos como &#x0D, ou quebras de linha. Um exemplo do padrão é:
                <exemplo>
                ELCILENE GOMES DA COSTA | 801578159&#x0D, R$ 55,00 | 1 |
                RONNY SOUZA LEITE | 94131716100&#x0D, R$ 53,80 | 1 |
                </exemplo>
                Seu objetivo é:
                - Limpar os artefatos como &#x0D, e normalizar o texto.
                - Identificar blocos compostos por: nome, CPF/CNPJ, valor e quantidade.
                - Corrigir campos em que o CPF/CNPJ e o valor estejam juntos, como: 94131716100 R$ 53,80, separando corretamente os dados.
                - Retornar os dados como uma lista estruturada de dicionários JSON com os seguintes campos:

                "nome": string
                "cpf_cnpj": string
                "valor": float (em formato decimal, e.g. 53.80)
                "quantidade": inteiro
                "tipo_transacao": string (presuma "crédito" se não indicado)
                "plataforma": string (presuma "PIX" se não indicado)

                Importante: O nome pode conter espaços; o CPF/CNPJ é numérico (com 11 ou 14 dígitos); o valor está sempre precedido por "R$".

                Você deve encontrar dados especialmente sobre essas pessoas: <envolvidos>{envolvidos}</envolvidos>

                ## ATENÇÃO. A sua resposta deve ser um objeto json [{{'nome': 'nome', 'cpf_cnpj': 'cpf/cnpj', 'tipo_transacao': 'tipo', 'valor': 'valor', 'quantidade': 'quantidade', 'plataforma': ''}}]. Não de nenhuma explicação, apenas o objeto json.

                <texto>{texto}</texto>"""

                # Salva no banco de dados
                _save_prompt_to_db(request, 'financeira', 'informacoes_adicionais',
                                   'Análise de Informações Adicionais', prompt_text)

            # Lista os envolvidos
            envolvidos = Envolvido.objects.filter(
                caso=caso_ativo, indexador=com.indexador, rif=com.rif).values_list('nome_envolvido', flat=True)

            # Usar prompt do banco
            detalhes_envolvidos = executar_prompt([{
                "role": "user",
                "content": prompt_text.format(
                    envolvidos=envolvidos,
                    texto=com.informacoes_adicionais
                )
            }])

            if detalhes_envolvidos:
                detalhes_envolvidos = json.loads(
                    detalhes_envolvidos.replace('json', '').replace('`', ''))

                # Salva no banco de dados
                for detalhe in detalhes_envolvidos:
                    print("*"*100)
                    print("*** DETALHE ***")
                    print(detalhe)
                    print("*"*100)

                    cpf_cnpj = validar_e_limpar_cpf_cnpj(detalhe['cpf_cnpj'])
                    valor = processar_valor_monetario(detalhe['valor'])
                    if valor > 0 and cpf_cnpj and cpf_cnpj != '':

                        # Cria uma nova informação adicional
                        InformacaoAdicional.objects.create(
                            rif=com.rif,
                            caso=caso_ativo,
                            arquivo=com.arquivo,
                            comunicacao=com,
                            indexador=com.indexador,
                            tipo_transacao=detalhe['tipo_transacao'],
                            cpf=validar_e_limpar_cpf_cnpj(detalhe['cpf_cnpj']),
                            nome=detalhe['nome'],
                            valor=processar_valor_monetario(detalhe['valor']),
                            transacoes=detalhe['quantidade'],
                            plataforma=detalhe['plataforma'],
                        )

                        print("SALVO")
                    else:
                        print("*** VALOR OU CPF/CNPJ INVÁLIDO ***")
            else:
                print("*** NENHUM DETALHE ENCONTRADO ***")

        # REFAZ A BUSCA

        # Busca as informações adicionais do caso ativo
        detalhes_envolvidos = InformacaoAdicional.objects.filter(
            caso=caso_ativo).select_related('comunicacao').order_by('indexador', 'nome')

        if detalhes_envolvidos:
            # Converte QuerySet para lista de dicionários
            detalhes_envolvidos = list(detalhes_envolvidos.values())

            # Arruma a coluna Valor para moeda(), mantendo as outras colunas
            for i, detalhe in enumerate(detalhes_envolvidos):
                detalhes_envolvidos[i]['valor_formatado'] = moeda(
                    detalhe['valor'])
                detalhes_envolvidos[i]['numero_rif'] = RIF.objects.get(
                    id=detalhe['rif_id']).numero

            # Calcula o total de envolvidos
            total_envolvidos = Envolvido.objects.filter(
                caso=caso_ativo).count()
            # Calcula o total de envolvidos sem informações
            total_sem_info = total_envolvidos - len(detalhes_envolvidos)
            # Calcula o percentual de envolvidos sem informações
            percentual_sem_info = int(
                (total_sem_info / total_envolvidos) * 100) if total_envolvidos > 0 else 0

            context = {
                'caso': caso_ativo,
                'informacoes_adicionais': detalhes_envolvidos,
                'total_envolvidos': total_envolvidos,
                'total_sem_info': total_sem_info,
                'percentual_sem_info': percentual_sem_info
            }

            return render(request, 'financeira/informacoes_adicionais.html', context)

        else:
            messages.warning(
                request, 'Nenhuma informação adicional encontrada.')
            return redirect('financeira:financeira_errosimportacao')

    except json.JSONDecodeError:
        messages.warning(
            request, 'Processando. Tente novamente em alguns instantes.')
        return redirect('financeira:financeira_comunicacoes')
    except Exception as e:
        print("***ERRO***", e)
        messages.error(request, 'Erro ao processar informações adicionais.')
        return redirect('financeira:financeira_comunicacoes')


@login_required
def financeira_analisedevinculos(request):
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')

    # Busca todos os envolvidos do caso ativo
    envolvidos = Envolvido.objects.filter(caso=caso_ativo)

    # Monta os nós (pessoas) usando CPF/CNPJ como identificador
    nodes = []
    node_ids = set()
    for e in envolvidos:
        cpf_cnpj = str(e.cpf_cnpj_envolvido)
        if cpf_cnpj not in node_ids:
            nodes.append({
                "id": cpf_cnpj,
                "nome": e.nome_envolvido,
                "cpf_cnpj": cpf_cnpj,
                "tipo": e.tipo_envolvido,
                "indexador": str(e.indexador),
            })
            node_ids.add(cpf_cnpj)

    # Monta os links (conexões) entre os nós
    links = []

    # Primeiro, encontra todos os titulares
    titulares = envolvidos.filter(tipo_envolvido='Titular')

    # Para cada titular, cria conexões com outros envolvidos que compartilham o mesmo indexador
    for titular in titulares:
        outros_envolvidos = envolvidos.filter(
            indexador=titular.indexador).exclude(id=titular.id)

        for outro in outros_envolvidos:
            links.append({
                "source": str(outro.cpf_cnpj_envolvido),
                "target": str(titular.cpf_cnpj_envolvido),
                "tipo": f"{outro.tipo_envolvido} -> Titular",
                "tipo_relacao": "Titular"
            })

    # Cria conexões entre redes quando o mesmo envolvido aparece em diferentes indexadores
    for cpf_cnpj in node_ids:

        if cpf_cnpj == '':
            continue

        envolvidos_mesmo_cpf = envolvidos.filter(cpf_cnpj_envolvido=cpf_cnpj)
        if envolvidos_mesmo_cpf.count() > 1:
            # Pega o primeiro envolvido como referência
            primeiro = envolvidos_mesmo_cpf.first()
            # Cria conexões com os outros envolvidos do mesmo CPF/CNPJ
            for outro in envolvidos_mesmo_cpf.exclude(id=primeiro.id):
                links.append({
                    "source": str(primeiro.cpf_cnpj_envolvido),
                    "target": str(outro.cpf_cnpj_envolvido),
                    "tipo": "Mesmo CPF/CNPJ"
                })

    context = {
        "nodes": nodes,
        "links": links,
        "caso": caso_ativo
    }
    return render(request, 'financeira/analisedevinculos.html', context)


@login_required
def download_vinculos_csv(request):
    """Endpoint para download dos dados de vínculos em formato CSV"""
    from core.templatetags.mask import real, mask

    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos')

    csv_data = []
    csv_data_informacoes_adicionais = []

    # Busca todas as comunicações do caso ativo
    comunicacoes = Comunicacao.objects.filter(caso=caso_ativo)

    for com in comunicacoes:
        # Busca os titulares da comunicação
        titulares = Envolvido.objects.filter(
            caso=caso_ativo, tipo_envolvido='Titular', indexador=com.indexador)
        for titular in titulares:
            # Busca os envolvidos da comunicação
            envolvidos = Envolvido.objects.filter(
                caso=caso_ativo, indexador=com.indexador)
            for envolvido in envolvidos:
                # Busca os dados da comunicação
                csv_data.append({
                    "tipo_registro": "comunicacao",
                    "id_comunicacao": com.id,
                    "numero_ocorrencia_bc": com.numero_ocorrencia_bc,
                    "data_recebimento": com.data_recebimento,
                    "data_operacao": com.data_operacao,
                    "data_fim_fato": com.data_fim_fato,
                    "cpf_cnpj_comunicante": mask(com.cpf_cnpj_comunicante, 'cpf_cnpj'),
                    "nome_comunicante": com.nome_comunicante,
                    "titular": titular.nome_envolvido,
                    "titular_cpf_cnpj": mask(titular.cpf_cnpj_envolvido, 'cpf_cnpj'),
                    "envolvido": envolvido.nome_envolvido,
                    "envolvido_cpf_cnpj": mask(envolvido.cpf_cnpj_envolvido, 'cpf_cnpj'),
                    "tipo_envolvido": envolvido.tipo_envolvido,
                    "indexador": str(envolvido.indexador),
                })

    # Busca todos os registros de informações adicionais do caso ativo
    informacoes_adicionais = InformacaoAdicional.objects.filter(
        caso=caso_ativo)
    for info in informacoes_adicionais:
        titular = Envolvido.objects.filter(
            caso=caso_ativo, tipo_envolvido='Titular', rif_id=info.rif_id, indexador=info.indexador).first()
        csv_data_informacoes_adicionais.append({
            "indexador": str(info.indexador),
            "tipo_transacao": info.tipo_transacao,
            "titular": titular.nome_envolvido,
            "titular_cpf_cnpj": mask(titular.cpf_cnpj_envolvido, 'cpf_cnpj'),
            "envolvido": info.nome,
            "envolvido_cpf_cnpj": mask(info.cpf, 'cpf_cnpj'),
            # Usa a templatetag real para formatar o valor
            "valor": real(info.valor),
            "plataforma": info.plataforma,
            "transacoes": info.transacoes,
        })

    # Cria DataFrame com todos os dados
    df = pd.DataFrame(csv_data)
    df_informacoes_adicionais = pd.DataFrame(csv_data_informacoes_adicionais)

    # Cria um arquivo temporário para o ZIP
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        # Cria o arquivo ZIP
        with zipfile.ZipFile(temp_file.name, 'w') as zf:
            # Adiciona os CSVs ao ZIP
            if not df.empty:
                csv_content = df.to_csv(index=False)
                zf.writestr('vinculos.csv', csv_content)

            if not df_informacoes_adicionais.empty:
                csv_content_informacoes_adicionais = df_informacoes_adicionais.to_csv(
                    index=False)
                zf.writestr('vinculos_informacoes_adicionais.csv',
                            csv_content_informacoes_adicionais)

            # Adiciona o arquivo de especificações do I2
            with open('utils/anexos/rif_vinculos.ximp', 'rb') as ximp_file:
                zf.writestr('Trace - RIF - Vínculos.ximp', ximp_file.read())
            with open('utils/anexos/rif_informacoes_adicionais.ximp', 'rb') as ximp_file:
                zf.writestr(
                    'Trace - RIF - Informações Adicionais.ximp', ximp_file.read())

        # Lê o arquivo ZIP
        with open(temp_file.name, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename=vinculos_{caso_ativo.numero}.zip'
            return response


@login_required
def download_vinculos_anx(request):
    """Endpoint para download dos dados de vínculos em formato ANX"""
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos')

    # Busca todos os envolvidos do caso ativo
    envolvidos = Envolvido.objects.filter(caso=caso_ativo)

    # Prepara os dados para o ANX (formato específico para análise de vínculos)
    anx_data = {
        "caso": {
            "numero": caso_ativo.numero
        },
        "nodes": [],
        "links": []
    }

    # Monta os nós (pessoas)
    node_ids = set()
    for e in envolvidos:
        cpf_cnpj = str(e.cpf_cnpj_envolvido)
        if cpf_cnpj not in node_ids:
            anx_data["nodes"].append({
                "id": cpf_cnpj,
                "nome": e.nome_envolvido,
                "cpf_cnpj": cpf_cnpj,
                "tipo": e.tipo_envolvido,
                "indexador": str(e.indexador),
                "metadata": {
                    "agencia": e.agencia_envolvido,
                    "conta": e.conta_envolvido,
                    "data_abertura": str(e.data_abertura_conta) if e.data_abertura_conta else None,
                    "data_atualizacao": str(e.data_atualizacao_conta) if e.data_atualizacao_conta else None,
                    "pep": e.bit_pep_citado,
                    "pessoa_obrigada": e.bit_pessoa_obrigada_citado,
                    "servidor": e.int_servidor_citado
                }
            })
            node_ids.add(cpf_cnpj)

    # Monta os links (conexões)
    titulares = envolvidos.filter(tipo_envolvido='Titular')
    for titular in titulares:
        outros_envolvidos = envolvidos.filter(
            indexador=titular.indexador).exclude(id=titular.id)

        for outro in outros_envolvidos:
            anx_data["links"].append({
                "source": str(outro.cpf_cnpj_envolvido),
                "target": str(titular.cpf_cnpj_envolvido),
                "tipo": f"{outro.tipo_envolvido} -> Titular",
                "tipo_relacao": "Titular",
                "metadata": {
                    "indexador": str(titular.indexador)
                }
            })

    # Cria conexões entre redes (mesmo CPF/CNPJ)
    for cpf_cnpj in node_ids:
        if cpf_cnpj == '':
            continue

        envolvidos_mesmo_cpf = envolvidos.filter(cpf_cnpj_envolvido=cpf_cnpj)
        if envolvidos_mesmo_cpf.count() > 1:
            primeiro = envolvidos_mesmo_cpf.first()
            for outro in envolvidos_mesmo_cpf.exclude(id=primeiro.id):
                anx_data["links"].append({
                    "source": str(primeiro.cpf_cnpj_envolvido),
                    "target": str(outro.cpf_cnpj_envolvido),
                    "tipo": "Mesmo CPF/CNPJ",
                    "metadata": {
                        "indexador_source": str(primeiro.indexador),
                        "indexador_target": str(outro.indexador)
                    }
                })

    # Cria a resposta com o arquivo ANX
    response = HttpResponse(json.dumps(anx_data, indent=2, ensure_ascii=False),
                            content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename=vinculos_{caso_ativo.numero}.anx'

    return response


@login_required
def financeira_dashboard(request):
    return render(request, 'financeira/dashboard.html')


@login_required
def financeira_errosimportacao(request):
    """Mostra envolvidos que não têm informações adicionais"""
    # Busca o caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos')

    # Busca todos os envolvidos do caso ativo
    envolvidos = Envolvido.objects.filter(caso=caso_ativo)

    # Busca todas as informações adicionais do caso
    info_adicionais = InformacaoAdicional.objects.filter(caso=caso_ativo)

    # Cria um set de CPFs que já têm informações adicionais
    cpfs_com_info = set(info_adicionais.values_list('cpf', flat=True))
    # Converte em INT
    cpfs_com_info = set(int(cpf) for cpf in cpfs_com_info)

    # Filtra envolvidos que não têm informações adicionais
    envolvidos_sem_info = []
    cpfs_processados = set()

    # Dicionário para contar envolvidos por indexador
    contagem_por_indexador = {}

    for envolvido in envolvidos:

        # Testa se o tipo_envolvido é "Remetente" ou "Beneficiário"
        if envolvido.tipo_envolvido not in ['Remetente', 'Beneficiário', 'Outros']:
            continue

        # Normaliza o CPF/CNPJ removendo pontuação
        cpf_cnpj_limpo = int(str(envolvido.cpf_cnpj_envolvido).replace(
            '.', '').replace('-', '').replace('/', ''))

        # Contagem por indexador
        indexador = str(envolvido.indexador)
        if indexador not in contagem_por_indexador:
            contagem_por_indexador[indexador] = {
                'total': 0,
                'sem_info': 0
            }
        contagem_por_indexador[indexador]['total'] += 1

        # Se já processamos este CPF/CNPJ ou tem informações adicionais, pula
        if cpf_cnpj_limpo in cpfs_processados or cpf_cnpj_limpo in cpfs_com_info:
            continue

        # Marca este CPF/CNPJ como processado
        cpfs_processados.add(cpf_cnpj_limpo)

        # Incrementa contador de não processados do indexador
        contagem_por_indexador[indexador]['sem_info'] += 1

        # Busca a comunicação relacionada
        comunicacao = Comunicacao.objects.filter(
            caso=caso_ativo,
            rif=envolvido.rif,
            indexador=envolvido.indexador
        ).first()

        if comunicacao:
            # Busca o titular do grupo
            titular = envolvidos.filter(
                rif=envolvido.rif,
                indexador=envolvido.indexador,
                tipo_envolvido='Titular'
            ).first()

            contagem_por_indexador[indexador]['comunicacao_id'] = comunicacao.id

            envolvidos_sem_info.append({
                'id': envolvido.id,
                'comunicacao_id': comunicacao.id,
                'rif_numero': envolvido.rif.numero,
                'indexador': envolvido.indexador,
                'nome_comunicante': comunicacao.nome_comunicante,
                'tipo_envolvido': envolvido.tipo_envolvido,
                'titular': envolvido.nome_envolvido,
                'cpf_cnpj': envolvido.cpf_cnpj_envolvido,
                'data_comunicacao': comunicacao.data_recebimento,
                'valor': comunicacao.campo_a,
                'informacoes_adicionais': comunicacao.informacoes_adicionais
            })

    # Ordena o dicionário de contagem por total de envolvidos (decrescente)
    contagem_ordenada = sorted(
        [{'indexador': k, **v} for k, v in contagem_por_indexador.items()],
        key=lambda x: x['total'],
        reverse=True
    )

    # Calcula totais
    total_envolvidos = len(envolvidos)
    total_sem_info = len(cpfs_processados)
    percentual_sem_info = (
        total_sem_info / total_envolvidos * 100) if total_envolvidos > 0 else 0

    context = {
        'caso': caso_ativo,
        'envolvidos_sem_info': envolvidos_sem_info,
        'total_envolvidos': total_envolvidos,
        'total_sem_info': total_sem_info,
        'percentual_sem_info': round(percentual_sem_info, 2),
        'contagem_por_indexador': contagem_ordenada
    }

    return render(request, 'financeira/errosimportacao.html', context)


@login_required
def listar_rifs(request):
    """Retorna uma lista de RIFs em formato JSON para o modal de importação"""
    # Busca o caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()

    rifs = RIF.objects.filter(caso=caso_ativo).select_related(
        'caso').order_by('-created_at')
    rifs_list = [{'id': rif.id, 'numero': rif.numero} for rif in rifs]
    return JsonResponse(rifs_list, safe=False)


@login_required
def importar_arquivos(request):
    """Importa os arquivos de comunicações, envolvidos e ocorrências para uma RIF"""

    # Busca o caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos')

    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Método não permitido'
        }, status=405)

    # Validar se o RIF foi selecionada
    rif_id = request.POST.get('rif')
    if not rif_id:
        return JsonResponse({
            'success': False,
            'errors': {
                'rif': ['Selecione uma RIF']
            }
        }, status=400)

    try:
        rif = RIF.objects.filter(caso=caso_ativo).get(id=rif_id)
    except RIF.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'RIF não encontrada'
        }, status=404)

    try:
        # Processar os arquivos
        # Processa cada arquivo enviado
        arquivos = {
            'comunicacoes': request.FILES.get('comunicacoes'),
            'envolvidos': request.FILES.get('envolvidos'),
            'ocorrencias': request.FILES.get('ocorrencias')
        }

        registros_totais = 0
        resultado = {}

        for tipo, arquivo in arquivos.items():
            if not arquivo:
                continue

            try:
                df = ler_arquivo(arquivo)
            except ValueError as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Erro ao processar arquivo {tipo}: {str(e)}'
                }, status=400)

            # Adiciona campos comuns
            df['rif_id'] = rif.id
            df['caso_id'] = rif.caso_id

            # Salva os dados do arquivo no banco de dados para não processar duas vezes
            hash_arquivo = sha256_dataframe(df.to_csv())
            arquivo = pd.DataFrame([{
                "caso_id": rif.caso_id,
                "external_id": rif.id,
                "tipo": tipo,
                "nome": arquivo.name,
                "hash": hash_arquivo,
                "registros": df.shape[0],
                "created_at": timezone.now()
            }])
            ids_arquivos = save_dataframe(arquivo, 'app_arquivo')
            df['arquivo_id'] = ids_arquivos[0]

            # Processa os dados do arquivo e salva no banco de dados
            try:
                conn = sqlite3.connect('db.sqlite3')

                if tipo == 'comunicacoes':
                    # Ajusta colunas
                    df = df.rename(
                        columns={'informacoesAdicionais': 'informacoes_adicionais'})
                    df = df.rename(columns={'CampoA': 'campo_a', 'CampoB': 'campo_b', 'CampoC': 'campo_c', 'CampoD': 'campo_d', 'CampoE': 'campo_e'})
                    
                    # Converte o campo_a para float
                    df['campo_a'] = df['campo_a'].apply(converter_valores)
                    df['campo_b'] = df['campo_b'].apply(converter_valores)
                    df['campo_c'] = df['campo_c'].apply(converter_valores)
                    df['campo_d'] = df['campo_d'].apply(converter_valores)
                    df['campo_e'] = df['campo_e'].apply(converter_valores)
                    
                    # Corrige colunas de data com tratamento de erro
                    for col in ['data_recebimento', 'data_operacao', 'data_fim_fato']:
                        if col in df.columns:
                            try:
                                # Primeiro tenta o formato com hora
                                df[col] = pd.to_datetime(df[col], format='%d/%m/%Y %H:%M:%S', errors='coerce')
                                # Se não funcionar, tenta apenas a data
                                if df[col].isna().all():
                                    df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
                                # Se ainda não funcionar, converte para string
                                df[col] = df[col].dt.strftime('%Y-%m-%d').fillna('')
                            except Exception as e:
                                print(f"Erro ao converter {col}: {e}")
                                df[col] = df[col].astype(str)

                    # Salva os dados do arquivo no banco de dados
                    df.to_sql('financeira_comunicacao', con=conn,
                              if_exists='append', index=False)
                    resultado['comunicacoes'] = len(df)

                elif tipo == 'envolvidos':
                    # Formata CPF/CNPJ
                    df['cpf_cnpj_envolvido'] = df['cpf_cnpj_envolvido'].str.replace(
                        r'\D', '', regex=True)

                    # Renomeia colunas
                    df = df.rename(columns={'nomeEnvolvido': 'nome_envolvido'})
                    df = df.rename(columns={'tipoEnvolvido': 'tipo_envolvido'})

                    # Normaliza o nome do envolvido
                    df['nome_envolvido'] = df['nome_envolvido'].apply(
                        lambda x: normalizar_nome(x))
                    
                    # Corrige colunas de data com tratamento de erro
                    for col in ['data_abertura_conta', 'data_atualizacao_conta']:
                        if col in df.columns:
                            try:
                                df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
                                df[col] = df[col].dt.strftime('%Y-%m-%d').fillna('')
                            except Exception as e:
                                print(f"Erro ao converter {col}: {e}")
                                df[col] = df[col].astype(str)
                                        
                    # Remove todas as linhas que o  Indexador não é um número
                    df = df[df['indexador'].astype(str).str.isnumeric()]

                    df.to_sql('financeira_envolvido', con=conn,
                              if_exists='append', index=False)
                    resultado['envolvidos'] = len(df)

                elif tipo == 'ocorrencias':
                    # Corrige colunas de data com tratamento de erro
                    for col in ['data_recebimento']:
                        if col in df.columns:
                            try:
                                df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')
                                df[col] = df[col].dt.strftime('%Y-%m-%d').fillna('').astype(str)
                            except Exception as e:
                                print(f"Erro ao converter {col}: {e}")
                                df[col] = df[col].astype(str)
                    
                    # Remove todas as linhas que o  Indexador não é um número
                    df = df[df['indexador'].astype(str).str.isnumeric()]
                    
                    df.to_sql('financeira_ocorrencia', con=conn,
                              if_exists='append', index=False)
                    resultado['ocorrencias'] = len(df)

            except Exception as e:
                print(e)
                return JsonResponse({
                    'success': False,
                    'message': f'Erro ao salvar {tipo}: {str(e)}'
                }, status=500)

            conn.close()
            registros_totais += len(df)

        # Atualiza contadores na RIF
        rif.total_comunicacoes = resultado.get('comunicacoes', 0)
        rif.total_envolvidos = resultado.get('envolvidos', 0)
        rif.save()

        return JsonResponse({
            'success': True,
            'message': 'Arquivos importados com sucesso!'
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao processar arquivos: {str(e)}'
        }, status=500)


def converter_valores(valor):
    """
    Converte valores monetários em formato texto para float.
    
    Esta função recebe um valor que pode estar em diferentes formatos (int, float ou string)
    e o converte para float. Se o valor estiver em formato brasileiro (usando vírgula como 
    separador decimal), faz a conversão apropriada.

    Args:
        valor: O valor a ser convertido, pode ser int, float ou string

    Returns:
        float: O valor convertido para float

    Exemplo:
        >>> converter_valores("1.234,56")
        1234.56
        >>> converter_valores(1234)
        1234.0
        >>> converter_valores("")
        0.0
    """
    if isinstance(valor, (int, float)):
        return valor  # Retorna diretamente se já for numérico

    if str(valor).count(',') > 0:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

        valor = locale.atof(valor)

    if valor == '':
        valor = 0

    return float(valor)


def save_dataframe(df, table_name, if_exists='append', index=False):
    try:

        # Testa se existe a coluna CPF no df
        coluna_cpf = next((col for col in ['cpf', 'CPF', 'cnpj', 'CNPJ', 'cpf_cnpj',
                          'cpfCnpjTitular', 'cpfCnpjEnvolvido'] if col in df.columns), None)
        if coluna_cpf:
            # Somente digitos (com RE)
            df[coluna_cpf] = df[coluna_cpf].str.replace(r'\D', '', regex=True)

        # Testa se existe a coluna de valor financeiro]
        for col in df.columns:
            if col in ['campo_a', 'campo_b', 'campo_c', 'campo_d', 'campo_e', 'valor']:
                df[col] = df[col].apply(converter_valores)

        # Tratar colunas de data para evitar problemas com formato brasileiro
        date_columns = [col for col in df.columns if 'data' in col.lower()]
        for col in date_columns:
            if col in df.columns:
                try:
                    # Tentar diferentes formatos de data
                    df[col] = df[col].astype(str)
                    # Primeiro tenta formato com hora
                    temp_dates = pd.to_datetime(df[col], format='%d/%m/%Y %H:%M:%S', errors='coerce')
                    # Se não funcionar, tenta apenas data
                    mask = temp_dates.isna()
                    if mask.any():
                        temp_dates[mask] = pd.to_datetime(df[col][mask], format='%d/%m/%Y', errors='coerce')
                    # Converte para string ISO
                    df[col] = temp_dates.dt.strftime('%Y-%m-%d').fillna('')
                except Exception as e:
                    print(f"Erro ao converter coluna {col}: {e}")
                    # Se falhar, mantém como string
                    df[col] = df[col].astype(str)

        #
        # SALVA NO BANCO DE DADOS
        #
        conn = sqlite3.connect('db.sqlite3')
        
        # Configurar pandas para não converter datas automaticamente
        df.to_sql(table_name, con=conn, if_exists='append', index=False, 
                  dtype={col: 'text' for col in df.columns if 'data' in col.lower()})

        # Obtém os IDs dos registros recém-inseridos
        result = conn.execute(
            f"SELECT id FROM {table_name} ORDER BY id DESC LIMIT :num", {'num': len(df)})
        ids = [row[0] for row in result]

        conn.close()

        return ids

    except Exception as e:
        print(f'Erro ao salvar o dataframe: {e}')
        insert_dataframe = False

    return insert_dataframe


def ler_arquivo(uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[-1].lower()
    nome_original = uploaded_file.name
    print(
        f'Extensão: {ext}, Tipo: {type(uploaded_file)}, Nome original: {nome_original}')
    # Salva o arquivo temporariamente
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(tmp_path)
        else:
            df = pd.read_csv(tmp_path, encoding='windows-1252',
                             delimiter=';', keep_default_na=False)
    finally:
        os.unlink(tmp_path)  # Remove o arquivo temporário

    if 'Indexador' not in df.columns:
        raise ValueError('Coluna "Indexador" não encontrada no arquivo.')

    condicao = (df['Indexador'].astype(str).str.strip() == '') | (
        df['Indexador'].astype(str).str.startswith('#'))
    indices = df[condicao].index

    # RENOMEAR TODAS AS COLUNAS
    # Mapeamento das colunas do DF para os nomes das colunas do modelo
    if 'Comunicacoes.csv' in nome_original:
        mapeamento_colunas = {
            'Indexador': 'indexador',
            'idComunicacao': 'id_comunicacao',
            'NumeroOcorrenciaBC': 'numero_ocorrencia_bc',
            'Data_do_Recebimento': 'data_recebimento',
            'Data_da_operacao': 'data_operacao',
            'DataFimFato': 'data_fim_fato',
            'cpfCnpjComunicante': 'cpf_cnpj_comunicante',
            'nomeComunicante': 'nome_comunicante',
            'CidadeAgencia': 'cidade_agencia',
            'UFAgencia': 'uf_agencia',
            'NomeAgencia': 'nome_agencia',
            'NumeroAgencia': 'numero_agencia',
            'informacoes_adicionais': 'informacoes_adicionais',
            'campo_a': 'campo_a',
            'campo_b': 'campo_b',
            'campo_c': 'campo_c',
            'campo_d': 'campo_d',
            'CampoE': 'campo_e',
            'CodigoSegmento': 'codigo_segmento'
        }
    elif 'Envolvidos.csv' in nome_original:
        mapeamento_colunas = {
            'Indexador': 'indexador',
            'cpfCnpjEnvolvido': 'cpf_cnpj_envolvido',
            'nome_envolvido': 'nome_envolvido',
            'tipo_envolvido': 'tipo_envolvido',
            'agenciaEnvolvido': 'agencia_envolvido',
            'contaEnvolvido': 'conta_envolvido',
            'DataAberturaConta': 'data_abertura_conta',
            'DataAtualizacaoConta': 'data_atualizacao_conta',
            'bitPepCitado': 'bit_pep_citado',
            'bitPessoaObrigadaCitado': 'bit_pessoa_obrigada_citado',
            'intServidorCitado': 'int_servidor_citado'
        }
    elif 'Ocorrencias.csv' in nome_original:
        mapeamento_colunas = {
            'Indexador': 'indexador',
            'idOcorrencia': 'id_ocorrencia',
            'Ocorrencia': 'ocorrencia'
        }
    else:
        raise ValueError(
            'Tipo de arquivo não reconhecido para mapeamento de colunas: ' + nome_original)

    # Renomear as colunas do DataFrame
    df = df.rename(columns=mapeamento_colunas)

    if not indices.empty:
        indice_parada = indices[0]
        df = df.iloc[:indice_parada]

    # Limpa colunas de data
    if 'data_abertura_conta' in df.columns:
        df['data_abertura_conta'] = df['data_abertura_conta'].replace(
            '-', None)
    if 'data_atualizacao_conta' in df.columns:
        df['data_atualizacao_conta'] = df['data_atualizacao_conta'].replace(
            '-', None)
    if 'data_recebimento' in df.columns:
        df['data_recebimento'] = df['data_recebimento'].replace('-', None)
    if 'data_operacao' in df.columns:
        df['data_operacao'] = df['data_operacao'].replace('-', None)
    if 'data_fim_fato' in df.columns:
        df['data_fim_fato'] = df['data_fim_fato'].replace('-', None)

    return df

##################################################################################################
# ENVOLVIDO DETALHES
##################################################################################################


@require_GET
def envolvido_detalhes(request, cpf_cnpj):
    """
    Mostra os detalhes de um envolvido na Análise de Vínculos
    Args:
        request (Request): Requisição HTTP atual
        cpf_cnpj (str): CPF/CNPJ do envolvido

    Returns:
        HttpResponse: Página renderizada com os detalhes do envolvido - MODAL

    Raises:
        Http404: Se o envolvido não for encontrado
        Exception: Se houver erro no processamento
    """

    caso_ativo = _buscar_caso_ativo(request)

    # Busca o envolvido
    envolvido = Envolvido.objects.filter(cpf_cnpj_envolvido=cpf_cnpj)

    if not envolvido:
        messages.error(request, 'Envolvido não encontrado.')
        return redirect('financeira:financeira_envolvidos')

    # Busca todas as comunicações relacionadas ao envolvido
    comunicacoes = Comunicacao.objects.filter(
        caso_id=caso_ativo.id,
        indexador__in=envolvido.values_list('indexador', flat=True)
    )

    for comunicacao in comunicacoes:
        comunicacao.titular = _buscar_titular_ocorrencia(comunicacao)
        comunicacao.envolvido = envolvido.filter(
            indexador=comunicacao.indexador).first()

    context = {
        'envolvido': envolvido.first(),
        'comunicacoes': comunicacoes,
    }

    return render(request, 'financeira/envolvido_detalhes.html', context)


@login_required
def comunicacoes_envolvido(request, cpf_cnpj_envolvido, rif_id):
    """
    Consulta todas as comunicações que o CPF consta no caso que o RIF está indicado
    """

    try:
        # Buscar o RIF
        rif = get_object_or_404(RIF, id=rif_id)

        # Buscar o envolvido em todos os RIFs do caso
        envolvidos = Envolvido.objects.filter(
            cpf_cnpj_envolvido=cpf_cnpj_envolvido, caso_id=rif.caso.id)
        comunicacoes = []

        for envolvido in envolvidos:
            # Buscar comunicações para este envolvido
            comunicacoes_envolvido = Comunicacao.objects.filter(
                rif__caso=rif.caso,
                indexador=envolvido.indexador
            ).order_by('-data_recebimento')

            # Buscar titular para este envolvido
            titular = Envolvido.objects.filter(
                indexador=envolvido.indexador, rif=rif, tipo_envolvido='Titular').first()

            # Adicionar informações do titular a cada comunicação
            for comunicacao in comunicacoes_envolvido:
                if titular:
                    comunicacao.titular = titular.nome_envolvido
                    comunicacao.cpf_cnpj_titular = titular.cpf_cnpj_envolvido
                else:
                    comunicacao.titular = "Não identificado"
                    comunicacao.cpf_cnpj_titular = "N/A"

            # Adicionar as comunicações à lista
            comunicacoes.extend(comunicacoes_envolvido)

        context = {
            'envolvido': envolvidos.first(),
            'rif': rif,
            'comunicacoes': comunicacoes,
            'caso': rif.caso
        }

        return render(request, 'financeira/comunicacoes_envolvido.html', context)

    except Exception as e:
        print(f"DEBUG: Erro na função comunicacoes_envolvido: {str(e)}")
        import traceback
        traceback.print_exc()
        messages.error(request, f'Erro ao buscar comunicações: {str(e)}')
        return redirect('financeira:financeira_envolvidos')


@login_required(login_url='/login')
def resumo(request):
    """Gera relatório financeiro do caso"""

    # Testa se tem um caso ativo.
    caso = _buscar_caso_ativo(request)

    # Buscar RIFs do caso
    rifs = RIF.objects.filter(caso=caso)

    # Buscar investigados do caso
    investigados = caso.investigados.all()

    # Buscar comunicações do caso
    comunicacoes = Comunicacao.objects.filter(caso=caso)

    # Buscar envolvidos do caso
    envolvidos = Envolvido.objects.filter(caso=caso)

    # Buscar informações adicionais
    informacoes_adicionais = InformacaoAdicional.objects.filter(caso=caso)

    # Buscar ocorrências
    ocorrencias = Ocorrencia.objects.filter(
        caso=caso).values('ocorrencia', 'indexador', 'id').distinct()

    total_movimentacao = sum(processar_valor_monetario(com.campo_a)
                             for com in comunicacoes if com.campo_a)
    total_creditos = sum(processar_valor_monetario(com.campo_b)
                         for com in comunicacoes if com.campo_b)
    total_debitos = sum(processar_valor_monetario(com.campo_c)
                        for com in comunicacoes if com.campo_c)

    # Preparar dados para o template
    context = {
        'caso': caso,
        'rifs': rifs,
        'investigados': investigados,
        'comunicacoes': comunicacoes,
        'envolvidos': envolvidos,
        'informacoes_adicionais': informacoes_adicionais,
        'ocorrencias': ocorrencias,
        'total_movimentacao': total_movimentacao,
        'total_creditos': total_creditos,
        'total_debitos': total_debitos,
    }

    return render(request, 'financeira/resumo.html', context)



##################################################################################################
#
# RELATORIOS 
# 
##################################################################################################
@login_required
def relatorio_documento(request):
    """Gera relatório financeiro do caso"""

    # Testa se tem um caso ativo.
    caso = _buscar_caso_ativo(request)
    
    

    # Buscar RIFs do caso
    rifs = RIF.objects.filter(caso=caso)
    comunicacoes = Comunicacao.objects.filter(caso=caso)
    envolvidos = Envolvido.objects.filter(caso=caso)
    ocorrencias = Ocorrencia.objects.filter(caso=caso)
    investigados = caso.investigados.all()

    # Converter RIFs para lista de dicionários
    rifs_list = []
    for rif in rifs:
        rifs_list.append({
            'id': rif.id,
            'numero': rif.numero,
            'caso': rif.caso,
            'movimentacao': 0  # Será atualizado abaixo
        })

    # Calcular movimentação para cada RIF
    for i, rif_dict in enumerate(rifs_list):
        movimentacao_rif = sum(processar_valor_monetario(com.campo_a)
                               for com in comunicacoes if com.caso == rif_dict['caso'])
        rifs_list[i]['movimentacao'] = moeda(movimentacao_rif)

    # Filtra os titulares e representantes
    titulares = envolvidos.filter(tipo_envolvido='Titular').values(
        'cpf_cnpj_envolvido', 'nome_envolvido', 'tipo_envolvido', 'indexador').distinct().order_by('nome_envolvido')
    representantes = envolvidos.filter(tipo_envolvido='Representante').values(
        'cpf_cnpj_envolvido', 'nome_envolvido', 'tipo_envolvido', 'indexador').distinct().order_by('nome_envolvido')

    # Total movimentado no Caso
    movimentacao = sum(processar_valor_monetario(com.campo_a)
                       for com in comunicacoes if com.campo_a)

    # Total movimentado por titular
    for i, titular in enumerate(titulares):
        movimentacao_titular = sum(processar_valor_monetario(
            com.campo_a) for com in comunicacoes if com.campo_a and com.indexador == titular['cpf_cnpj_envolvido'])
        titulares[i]['movimentacao'] = moeda(movimentacao_titular)
        titulares[i]['creditos'] = moeda(sum(processar_valor_monetario(
            com.campo_b) for com in comunicacoes if com.indexador == titular['indexador']))
        titulares[i]['debitos'] = moeda(sum(processar_valor_monetario(
            com.campo_c) for com in comunicacoes if com.indexador == titular['indexador']))

    df_rifdetalhado = pd.DataFrame()

    # Converter QuerySets para DataFrames com as colunas corretas
    df_comunicacoes = pd.DataFrame(list(comunicacoes.values(
        'rif__id', 'rif__numero', 'informacoes_adicionais', 'campo_a', 'campo_b', 'campo_c', 'campo_d', 'campo_e', 'codigo_segmento')))
    df_envolvidos = pd.DataFrame(list(envolvidos.values(
        'rif__id', 'rif__numero', 'nome_envolvido', 'tipo_envolvido', 'indexador', 'cpf_cnpj_envolvido')))
    df_ocorrencias = pd.DataFrame(
        list(ocorrencias.values('rif__id', 'rif__numero', 'ocorrencia')))

    # Renomear colunas para usar 'rif__id' como chave de merge
    df_comunicacoes = df_comunicacoes.rename(
        columns={'rif__id': 'rif_id', 'rif__numero': 'numero_rif'})
    df_envolvidos = df_envolvidos.rename(
        columns={'rif__id': 'rif_id', 'rif__numero': 'numero_rif'})
    df_ocorrencias = df_ocorrencias.rename(
        columns={'rif__id': 'rif_id', 'rif__numero': 'numero_rif'})

    # Juntar Comunicacao, Envolvido e Ocorrencia no df_rifdetalhado
    if not df_comunicacoes.empty:
        df_rifdetalhado = df_comunicacoes
    if not df_envolvidos.empty:
        if df_rifdetalhado.empty:
            df_rifdetalhado = df_envolvidos
        else:
            df_rifdetalhado = df_rifdetalhado.merge(
                df_envolvidos, on=['rif_id', 'numero_rif'], how='left')
    if not df_ocorrencias.empty:
        if df_rifdetalhado.empty:
            df_rifdetalhado = df_ocorrencias
        else:
            df_rifdetalhado = df_rifdetalhado.merge(
                df_ocorrencias, on=['rif_id', 'numero_rif'], how='left')

    

    # Monta os dados para cada alvo
    titulares_extratos = []
    todas_informacoes_adicionais = []
    for titular in titulares:
        alvo = titular['nome_envolvido']

        # Filtrar o DataFrame para o titular atual
        df_alvo = df_rifdetalhado[
            (df_rifdetalhado['nome_envolvido'] == alvo) &
            (df_rifdetalhado['tipo_envolvido'] == 'Titular')
        ].copy()
        
        # Lista todos os envolvidos que aparecem nas comunicacoes do alvo
        envolvidos_com_alvo = []
        for index, row in df_alvo.iterrows():
            env = Envolvido.objects.filter(rif=row['rif_id'], indexador=titular['indexador'], caso=caso)
            #print(env)
            #print('-'*100)
            
            if env:
                # Testa se o envolvido já está na lista
                if env not in envolvidos_com_alvo:
                    envolvidos_com_alvo.append(env)
            

        if df_alvo.empty:
            continue

        # Resultado financeiro separado por alvo (movimentação total)
        df_alvo.loc[:, 'campo_a'] = pd.to_numeric(
            df_alvo['campo_a'], errors='coerce')
        movimentacao = df_alvo['campo_a'].sum()
        df_alvo['campo_a'] = df_alvo['campo_a'].apply(moeda)

        df_alvo.loc[:, 'campo_b'] = pd.to_numeric(
            df_alvo['campo_b'], errors='coerce')
        creditos = df_alvo['campo_b'].sum()
        df_alvo['campo_b'] = df_alvo['campo_b'].apply(moeda)

        df_alvo.loc[:, 'campo_c'] = pd.to_numeric(
            df_alvo['campo_c'], errors='coerce')
        debitos = df_alvo['campo_c'].sum()
        df_alvo['campo_c'] = df_alvo['campo_c'].apply(moeda)


        # INFORMAÇÕES ADICIONAIS
        infomacoes_adicionais = []
        for informacao in df_alvo['informacoes_adicionais'].dropna():
            infomacoes_adicionais.append(informacao)

        todas_informacoes_adicionais.append(infomacoes_adicionais)
        
        # 

        # OBSERVAÇÕES DO ANALISTA COM < IA >
        informacoes_texto = ' '.join(
            df_alvo['informacoes_adicionais'].dropna())
        # observacoes_analista = executar_prompt([{
        #    "role": "user",
        #    "content": f"Faça uma breve análise, em formato dissertativo, com um ou dois parágrafos, dessas movimentações bancárias. Anote com quem {alvo} transacionou dinheiro: <movimentacoes_bancarias>{informacoes_texto[0:3000]}</movimentacoes_bancarias>"
        # }])

        # KYC - Know Your Client
        # TODO a ideia é que o usuário possa criar um banco de dados customizado e integrar esses dados dentro do relatório
        kyc = ''  # executar_prompt([{
        #    "role": "user",
        #    "content": (f"Preciso fazer uma análise do tipo KYC (know your client) a partir das fichas de anotações de **{alvo}**. Identifique dados como CPF, Profissão, Renda, Bancos que mantém relacionamento, Empresas que é sócio ou tem alguma participação, Período em que os dados foram analisados. Foque ESPECIFICAMENTE nas informações de KYC, e ignore o restante das informações: <anotacoes>{informacoes_texto[0:3000]}</anotacoes>. Escreva um texto de um ou dois paragrafos com essas informações.")
        # }])
        
        # Envolvimentos em RIFs (agrupado por rif_id e indexador)
        df_env_alvo = df_envolvidos.loc[
            df_envolvidos['nome_envolvido'] == alvo,
            ['rif_id', 'indexador', 'nome_envolvido', 'tipo_envolvido', 'cpf_cnpj_envolvido']
        ].copy()
        df_envolvimentos_grouped = (
            df_env_alvo
            .drop_duplicates(subset=['rif_id', 'indexador'])
            .sort_values(['rif_id', 'indexador'])
            .reset_index(drop=True)
        )
        
        # TRANSACOES: Pesquisa na tabela InformacaoAdicional
        # ids puros
        indexadores = (
            df_envolvimentos_grouped['indexador']
            .dropna().astype(int).tolist()
        )
        print(indexadores)
        rif_ids = (
            df_envolvimentos_grouped['rif_id']
            .dropna().astype(int).tolist()
        )
        print(rif_ids)

        transacoes = []
        if indexadores and rif_ids:
            transacoes_qs = InformacaoAdicional.objects.filter(
                caso=caso,
                rif_id__in=rif_ids,
                indexador__in=indexadores,
            )
            transacoes = list(transacoes_qs.values(
                'rif_id', 'comunicacao_id', 'indexador',
                'tipo_transacao', 'cpf', 'nome', 'valor', 'transacoes', 'plataforma'
            ))
        print(transacoes)

        # Fallback por CPF (se quiser ampliar o match)
        if not transacoes and 'cpf_cnpj_envolvido' in df_envolvimentos_grouped.columns:
            cpfs = (
                df_envolvimentos_grouped['cpf_cnpj_envolvido']
                .dropna().astype(str)
                .str.replace(r'[^0-9]', '', regex=True)
                .tolist()
            )
            if cpfs:
                transacoes_qs = InformacaoAdicional.objects.filter(
                    caso=caso,
                    cpf__in=cpfs
                )
                transacoes = list(transacoes_qs.values(
                    'rif_id', 'comunicacao_id', 'indexador',
                    'tipo_transacao', 'cpf', 'nome', 'valor', 'transacoes', 'plataforma'
                ))
        
            print(transacoes)

        titulares_extratos.append({
            'nome': alvo,
            'investigado': False,  # Valor padrão
            'cpf': titular['cpf_cnpj_envolvido'],
            'kyc': kyc,
            'movimentacao_total': moeda(movimentacao),
            'creditos': moeda(creditos),
            'debitos': moeda(debitos),
            'comunicacoes_nao_suspeitas': [],
            'informacoes_adicionais_texto': infomacoes_adicionais,
            
            'transacoes': transacoes,
            
            
            'observacoes_analista': '',  # observacoes_analista,
            'ocorrencias': list(ocorrencias.filter(indexador=titular['indexador']).values('ocorrencia')),
            'envolvidos': envolvidos_com_alvo,
            'envolvimentos': df_envolvimentos_grouped.to_dict(orient='records'),
        })


    # Executa queries customizadas
    queries = [
        {  
            'name': 'Comunicações com campo_a > 10000',
            'query': 'SELECT * FROM financeira_comunicacao WHERE caso_id in (SELECT id from app_caso where ativo = TRUE) and campo_a > 10'
        }
    ]
    #custom_queries_result = get_custom_queries_results(queries)
    
    #print(custom_queries_result)
    custom_queries_result = []
    
    
    # Dados que serão impressos no relatório
    data = {
        'caso': caso,
        'arquivos': Arquivo.objects.filter(caso=caso),
        'rifs': rifs,
        'comunicacoes': comunicacoes,
        'envolvidos': envolvidos,
        'investigados': investigados,
        'titulares': titulares,
        'representantes': representantes,
        'ocorrencias': ocorrencias,
        'movimentacao': moeda(movimentacao),
        'titulares_extratos': titulares_extratos,
        'custom_queries': custom_queries_result,
    }
    
    try:
        # Carrega todos os relatórios com tipo 'financeiro'
        relatorios = Relatorio.objects.filter(tipo='financeiro')

        for relatorio in relatorios:
            print(relatorio.tipo)
            if relatorio.tipo == 'financeiro':
                doc = DocxTemplate(relatorio.arquivo.path)
                doc.render(data)

                # Cria um arquivo temporário com nome único
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
                temp_path = temp_file.name
                temp_file.close()

                # Salva o documento no arquivo temporário
                doc.save(temp_path)

                # Coloca em um .zip e manda para o cliente
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                    zip_file.write(temp_path, 'Relatorio Inteligência Financeira.docx')
                    
                    for alvo in titulares_extratos:
                        envolvimentos_alvo = alvo.get('envolvimentos')
                        if envolvimentos_alvo:
                            df_env_alvo = pd.DataFrame(envolvimentos_alvo)
                            excel_buffer = BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                                df_env_alvo.to_excel(writer, index=False)
                            zip_file.writestr(f'{alvo["nome"]}.xlsx', excel_buffer.getvalue())

                # Remove o arquivo temporário
                try:
                    os.unlink(temp_path)
                except:
                    pass

        # Envia o arquivo para o cliente
        response = HttpResponse(zip_buffer.getvalue(),
                                content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="Relatorio Inteligência Financeira.zip"'
        return response

    except Exception as e:
        print(e)
        return redirect('/financeira/index/')


##################################################################################################
# COMUNICAÇÃO DETALHES
##################################################################################################
@login_required
def comunicacao_detalhes(request, comunicacao_id):
    """
    Exibe detalhes completos de uma comunicação específica.

    Esta função busca e exibe informações detalhadas sobre uma comunicação,
    incluindo envolvidos, ocorrências e informações adicionais relacionadas.

    Args:
        request (Request): Requisição HTTP atual
        comunicacao_id (int): ID da comunicação a ser detalhada

    Returns:
        HttpResponse: Página renderizada com os detalhes da comunicação

    Raises:
        Http404: Se a comunicação não for encontrada
        Exception: Se houver erro no processamento
    """
    try:

        # Buscar a comunicação
        comunicacao = get_object_or_404(Comunicacao, id=comunicacao_id)

        # Buscar envolvidos relacionados a esta comunicação
        envolvidos = Envolvido.objects.filter(
            rif=comunicacao.rif,
            indexador=comunicacao.indexador
        ).order_by('tipo_envolvido')

        # Separar envolvidos por tipo para facilitar a exibição
        titulares = envolvidos.filter(tipo_envolvido='Titular')
        remetentes = envolvidos.filter(tipo_envolvido='Remetente')
        beneficiarios = envolvidos.filter(tipo_envolvido='Beneficiário')
        outros_envolvidos = envolvidos.exclude(
            tipo_envolvido__in=['Titular', 'Remetente', 'Beneficiário'])

        # Buscar ocorrências relacionadas
        ocorrencias = Ocorrencia.objects.filter(
            rif=comunicacao.rif,
            indexador=comunicacao.indexador
        ).order_by('id_ocorrencia')

        # Buscar informações adicionais relacionadas
        # Primeiro tenta com todos os filtros
        informacoes_adicionais = InformacaoAdicional.objects.filter(
            rif=comunicacao.rif,
            indexador=comunicacao.indexador,
            comunicacao=comunicacao
        ).order_by('id')

        # Se não encontrar, tenta sem o filtro de comunicação
        if informacoes_adicionais.count() == 0:
            informacoes_adicionais = InformacaoAdicional.objects.filter(
                rif=comunicacao.rif,
                indexador=comunicacao.indexador
            ).order_by('id')

        # Mapear valores de informacoes_adicionais por CPF
        info_adicionais_map = {}
        for info in informacoes_adicionais:
            try:
                # Primeiro tenta validar o CPF
                cpf = validar_e_limpar_cpf_cnpj(info.cpf)
                if cpf:
                    info_adicionais_map[cpf] = info
                else:
                    # Se não conseguir validar, usa o CPF original limpo (apenas números)
                    cpf_limpo = ''.join(filter(str.isdigit, str(info.cpf)))
                    info_adicionais_map[cpf_limpo] = info
            except Exception as e:
                # Em caso de erro, usa o CPF original limpo
                cpf_limpo = ''.join(filter(str.isdigit, str(info.cpf)))
                info_adicionais_map[cpf_limpo] = info

        # Adicionar info_adicional correspondente a cada remetente e beneficiário
        for envolvido in list(remetentes) + list(beneficiarios):
            try:
                # Primeiro tenta validar o CPF do envolvido
                cpf_env = validar_e_limpar_cpf_cnpj(
                    envolvido.cpf_cnpj_envolvido)
                if not cpf_env:
                    # Se não conseguir validar, usa o CPF original limpo
                    cpf_env = ''.join(
                        filter(str.isdigit, str(envolvido.cpf_cnpj_envolvido)))

                info = info_adicionais_map.get(cpf_env)
                setattr(envolvido, 'info_adicional', info if info else None)

            except Exception as e:
                print(
                    f"Erro ao processar envolvido {envolvido.nome_envolvido}: {str(e)}")
                # Em caso de erro, tenta com CPF limpo
                try:
                    cpf_env = ''.join(
                        filter(str.isdigit, str(envolvido.cpf_cnpj_envolvido)))
                    info = info_adicionais_map.get(cpf_env)
                    setattr(envolvido, 'info_adicional',
                            info if info else None)
                except:
                    setattr(envolvido, 'info_adicional', None)

        # Buscar dados KYC relacionados
        try:
            kyc_data = KYC.objects.filter(
                rif=comunicacao.rif,
                indexador=comunicacao.indexador,
                comunicacao=comunicacao
            ).first()
        except Exception as e:
            print(f"Erro ao buscar dados KYC: {str(e)}")
            kyc_data = None

        # Preparar dados financeiros
        dados_financeiros = {
            'campo_a': comunicacao.campo_a,
            'campo_b': comunicacao.campo_b,
            'campo_c': comunicacao.campo_c,
            'campo_d': comunicacao.campo_d,
            'campo_e': comunicacao.campo_e,
        }

        # Verificar se o segmento é diferente de 41 (padrão)
        segmento_alerta = None
        if comunicacao.codigo_segmento != 41:
            segmento_alerta = {
                'codigo_atual': comunicacao.codigo_segmento,
                'codigo_padrao': 41,
                'mensagem': f'ATENÇÃO: O segmento {comunicacao.codigo_segmento} é diferente do padrão (41)'
            }

        # Buscar prompt do banco de dados
        prompt_text = _get_prompt_from_db(
            'financeira', 'comunicacao_detalhes', 'Análise das informações adicionais da Comunicação')

        if prompt_text:
            # Análise por IA usando prompt do banco
            prompt_ia = [
                {
                    "role": "user",
                    "content": prompt_text.replace('{comunicacao}', comunicacao.informacoes_adicionais)
                }
            ]
        else:
            # Prompt padrão caso não encontre no banco
            prompt_ia = [
                {
                    "role": "user",
                    "content": f"""Organize os dados da comunicação financeira a seguir. Faça uma análise que contemple:
                                    1. Informações pessoais sobre o cadastrado (Cadastro, Profissão, sócio de empresa, renda/salário, Know Yout Client - KYC):
                                    2. Período analisado:
                                    3. Movimentações a crédito (também chamado de Origem dos recursos):
                                    4. Movimentações a débito (destino dos recursos):
                                    5. Caracteristicas das movimentações financeiras:
                                    6. Outras informações relevantes:

                                    <comunicacao>
                                    {comunicacao.informacoes_adicionais}
                                    </comunicacao>"""
                }
            ]

        # Verificar se já existe análise da IA para esta comunicação
        analise_ia = AnaliseIA.objects.filter(
            caso=comunicacao.caso,
            comunicacao=comunicacao
        ).first()

        # Se não existir análise, processa e salva
        if not analise_ia:
            analise_ia = executar_prompt(prompt_ia)

            # Salvar a análise no banco de dados
            analise_ia = AnaliseIA.objects.create(
                caso=comunicacao.caso,
                comunicacao=comunicacao,
                analise_ia=analise_ia
            )

        # Serializar os dados dos envolvidos para o diagrama
        def serializar_envolvidos(queryset):
            dados = [{'nome_envolvido': e.nome_envolvido, 'tipo_envolvido': e.tipo_envolvido,
                      'cpf_cnpj_envolvido': e.cpf_cnpj_envolvido} for e in queryset]
            print(f"Serializando {len(dados)} envolvidos")
            return dados

        # Serializar os dados
        titulares_json = serializar_envolvidos(titulares)
        remetentes_json = serializar_envolvidos(remetentes)
        beneficiarios_json = serializar_envolvidos(beneficiarios)
        outros_json = serializar_envolvidos(outros_envolvidos)

        # Inicializar o texto com as informações adicionais da comunicação
        texto = comunicacao.informacoes_adicionais

        # Destacar os envolvidos no texto de informações adicionais
        for envolvido in envolvidos:
            # Pesquisa os nomes sem acentos
            if envolvido.nome_envolvido and unidecode(envolvido.nome_envolvido).upper() in unidecode(texto).upper():
                def replacer(match):
                    return f'<span style="border-bottom: 2px dotted red;">{match.group()}</span>'

                texto = replace_ignorando_acentos(
                    texto, envolvido.nome_envolvido, replacer)

        comunicacao.informacoes_adicionais = texto

        # Procurar links de notícias no texto de informações adicionais
        re_links_noticias = re.findall(
            r'https?://[^\s]+', comunicacao.informacoes_adicionais)
        links_noticias = []
        for link in re_links_noticias:
            # Remover pontuação no final do link se houver
            link_limpo = re.sub(r'[.,;]$', '', link)
            comunicacao.informacoes_adicionais = comunicacao.informacoes_adicionais.replace(
                link,
                f'<a href="{link_limpo}" target="_blank" class="link-noticia">{link_limpo}</a>'
            )
            links_noticias.append(link_limpo)

        context = {
            'comunicacao': comunicacao,
            'envolvidos': envolvidos,
            'titulares': titulares,
            'remetentes': remetentes,
            'beneficiarios': beneficiarios,
            'outros_envolvidos': outros_envolvidos,

            'titulares_json': titulares_json,
            'remetentes_json': remetentes_json,
            'beneficiarios_json': beneficiarios_json,
            'outros_json': outros_json,

            'ocorrencias': ocorrencias,
            'informacoes_adicionais': informacoes_adicionais,
            'kyc_data': kyc_data,
            'dados_financeiros': dados_financeiros,
            'segmento_alerta': segmento_alerta,
            'analise_ia': analise_ia.analise_ia if analise_ia else None,
            'links_noticias': links_noticias,
        }

        return render(request, 'financeira/comunicacao_detalhes.html', context)

    except Exception as e:
        print("***ERRO***", e)
        messages.error(
            request, f'Erro ao carregar detalhes da comunicação: {str(e)}')
        return redirect('financeira:financeira_comunicacoes')


##################################################################################################
# PROMPTS
##################################################################################################
@login_required
def prompts_list(request):
    """Lista todos os prompts"""
    prompts = Prompt.objects.all().order_by('modulo', 'funcao', 'label')
    context = {
        'prompts': prompts,
    }
    return render(request, 'financeira/prompts/list.html', context)


@login_required
def prompt_create(request):
    """Cria um novo prompt"""
    if request.method == 'POST':
        try:
            modulo = request.POST.get('modulo')
            funcao = request.POST.get('funcao')
            label = request.POST.get('label')
            prompt = request.POST.get('prompt')
            description = request.POST.get('description', '')
            parameters = request.POST.get('parameters', '{}')
            is_active = request.POST.get('is_active') == 'on'

            # Validar campos obrigatórios
            if not all([modulo, funcao, label, prompt]):
                return JsonResponse({
                    'success': False,
                    'message': 'Todos os campos obrigatórios devem ser preenchidos.'
                }, status=400)

            # Verificar se já existe um prompt com a mesma combinação
            if Prompt.objects.filter(modulo=modulo, funcao=funcao, label=label).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Já existe um prompt com esta combinação de módulo, função e label.'
                }, status=400)

            # Criar o prompt
            novo_prompt = Prompt.objects.create(
                modulo=modulo,
                funcao=funcao,
                label=label,
                prompt=prompt,
                description=description,
                parameters=parameters,
                is_active=is_active,
                created_by=request.user
            )

            return JsonResponse({
                'success': True,
                'message': 'Prompt criado com sucesso!',
                'data': {
                    'id': novo_prompt.id,
                    'modulo': novo_prompt.modulo,
                    'funcao': novo_prompt.funcao,
                    'label': novo_prompt.label
                }
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao criar prompt: {str(e)}'
            }, status=500)

    return render(request, 'financeira/prompts/create.html')
















@login_required
def prompt_edit(request, prompt_id):
    """Edita um prompt existente"""
    prompt = get_object_or_404(Prompt, id=prompt_id)

    if request.method == 'POST':
        try:
            modulo = request.POST.get('modulo')
            funcao = request.POST.get('funcao')
            label = request.POST.get('label')
            prompt_text = request.POST.get('prompt')
            description = request.POST.get('description', '')
            parameters = request.POST.get('parameters', '{}')
            is_active = request.POST.get('is_active') == 'on'

            # Validar campos obrigatórios
            if not all([modulo, funcao, label, prompt_text]):
                return JsonResponse({
                    'success': False,
                    'message': 'Todos os campos obrigatórios devem ser preenchidos.'
                }, status=400)

            # Verificar se já existe outro prompt com a mesma combinação
            existing_prompt = Prompt.objects.filter(
                modulo=modulo,
                funcao=funcao,
                label=label
            ).exclude(id=prompt_id)

            if existing_prompt.exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Já existe outro prompt com esta combinação de módulo, função e label.'
                }, status=400)

            # Atualizar o prompt
            prompt.modulo = modulo
            prompt.funcao = funcao
            prompt.label = label
            prompt.prompt = prompt_text
            prompt.description = description
            prompt.parameters = parameters
            prompt.is_active = is_active
            prompt.save()

            return JsonResponse({
                'success': True,
                'message': 'Prompt atualizado com sucesso!',
                'data': {
                    'id': prompt.id,
                    'modulo': prompt.modulo,
                    'funcao': prompt.funcao,
                    'label': prompt.label
                }
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro ao atualizar prompt: {str(e)}'
            }, status=500)

    context = {
        'prompt': prompt,
    }
    return render(request, 'financeira/prompts/edit.html', context)






















@login_required
def prompt_delete(request, prompt_id):
    """Exclui um prompt"""
    prompt = get_object_or_404(Prompt, id=prompt_id)

    try:
        prompt.delete()
        return JsonResponse({
            'success': True,
            'message': 'Prompt excluído com sucesso!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro ao excluir prompt: {str(e)}'
        }, status=500)


@login_required
def prompt_toggle_active(request, prompt_id):
    """Ativa/desativa um prompt"""
    print(f"DEBUG: Função toggle chamada para prompt_id: {prompt_id}")
    prompt = get_object_or_404(Prompt, id=prompt_id)

    try:
        prompt.is_active = not prompt.is_active
        prompt.save()

        status = 'ativado' if prompt.is_active else 'desativado'
        print(f"DEBUG: Prompt {status} com sucesso")
        return JsonResponse({
            'success': True,
            'message': f'Prompt {status} com sucesso!',
            'data': {
                'is_active': prompt.is_active
            }
        })
    except Exception as e:
        print(f"DEBUG: Erro ao alterar status: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Erro ao alterar status do prompt: {str(e)}'
        }, status=500)


@login_required
def prompts_test(request):
    """Página de teste para prompts"""
    return render(request, 'financeira/prompts/test.html')


























##################################################################################################
# REPROCESSAR COMUNICAÇÃO - IA
##################################################################################################
@login_required
def processar_comunicacao(request, comunicacao_id):
    """
    Reprocessa uma comunicação específica usando IA
    """
    try:
        # Busca a comunicação
        comunicacao = get_object_or_404(Comunicacao, id=comunicacao_id)

        # Busca todas as informações adicionais do mesmo caso+rif+indexador
        informacoes_adicionais = InformacaoAdicional.objects.filter(
            caso=comunicacao.caso,
            rif=comunicacao.rif,
            indexador=comunicacao.indexador
        )

        # Monta o texto completo com todas as informações adicionais e elimina caracteres problemáticos
        caracteres_problematicos = ['&#x0D;', '&#x0D', '&#x0A;', '&#x0A']
        for caractere in caracteres_problematicos:
            texto_completo = comunicacao.informacoes_adicionais.replace(
                caractere, '')

        texto_processado = ""
        if informacoes_adicionais:
            for info in informacoes_adicionais[:1]:
                # Converte os campos relevantes do objeto para CSV
                campos = [
                    str(info.cpf),
                    info.nome,
                    info.tipo_transacao,
                    str(info.valor),
                    str(info.transacoes),
                    info.plataforma
                ]
                texto_processado += ",".join(campos) + "\n"

        # Lista de envolvidos
        envolvidos = Envolvido.objects.filter(
            caso=comunicacao.caso,
            rif=comunicacao.rif,
            indexador=comunicacao.indexador
        )

        envolvidos_sem_info = envolvidos.exclude(
            cpf_cnpj_envolvido__in=InformacaoAdicional.objects.filter(
                caso=comunicacao.caso,
                rif=comunicacao.rif,
                indexador=comunicacao.indexador
            ).values_list('cpf', flat=True)
        )
        # Envolvidos que não tem informações adicionais em formato de lista
        envolvidos_sem_info_list = [
            str(envolvido.nome_envolvido) for envolvido in envolvidos_sem_info]
        envolvidos_sem_info_str = ", ".join(envolvidos_sem_info_list[:20 if len(
            envolvidos_sem_info_list) > 20 else len(envolvidos_sem_info_list)])

        # Remove do texto o nome dos envolvidos que JÁ TEM informações adicionais, para evitar que ele colete novamente
        for envolvido in envolvidos_sem_info:
            texto_completo = texto_completo.replace(
                envolvido.nome_envolvido, '')

        print(texto_completo)

        # Buscar prompt do banco de dados
        prompt_text = _get_prompt_from_db(
            'financeira', 'informacoes_adicionais', 'Análise de Informações Adicionais')

        if prompt_text:
            # Usar prompt do banco
            detalhes_envolvidos = executar_prompt([{
                "role": "user",
                "content": prompt_text.format(texto=texto_completo)
            }, {
                "role": "user",
                "content": f"# Você precisa identificar os envolvidos que não tem informações adicionais. <envolvidos_sem_info>{envolvidos_sem_info_str}</envolvidos_sem_info>"
            }])
        else:
            # Prompt padrão caso não encontre no banco
            detalhes_envolvidos = executar_prompt([{
                "role": "user",
                "content": f"""Você é um especialista em investigação financeira e lavagem de dinheiro. Identifique, no texto, os envolvidos (nome e cpf/cnpj) o tipo de transação (crédito, débito) o valor (R$) e a quantidade. O Campo plataforma pode ser 'PIX', 'Depósito', 'Transferência' ou outras referência que você encontrar - se não encontrar algo explicito, deixe em branco. 
                
                Você precisa identificar ESPECIALMENTE essas pessoas: <envolvidos>{envolvidos_sem_info_str}</envolvidos>
                
                ATENÇÃO. A sua resposta deve ser um objeto json [{{'nome': 'nome', 'cpf_cnpj': 'cpf/cnpj', 'tipo_transacao': 'tipo', 'valor': 'valor', 'quantidade': 'quantidade', 'plataforma': ''}}]. Não de nenhuma explicação, apenas o objeto json.
                
                <texto>{texto_completo}</texto>"""
            }])

        if detalhes_envolvidos:

            print(detalhes_envolvidos)

            try:
                # Limpa a resposta da IA removendo marcadores de código
                resposta_limpa = detalhes_envolvidos.replace(
                    '```json', '').replace('```', '').replace('`', '').strip()

                # Tenta fazer o parse do JSON
                detalhes_envolvidos_json = json.loads(resposta_limpa)

                print(detalhes_envolvidos_json)

                if not detalhes_envolvidos_json:
                    print('sem detalhes')
                    messages.info(
                        request, 'Nenhuma informação adicional foi extraída pela IA.')
                    return redirect('financeira:financeira_errosimportacao')

                # Salva no banco de dados
                registros_salvos = 0
                for detalhe in detalhes_envolvidos_json:
                    cpf_cnpj = detalhe.get('cpf_cnpj', '')
                    if not cpf_cnpj:
                        continue  # Pula se não há CPF/CNPJ

                    cpf_limpo = cpf_cnpj.replace(
                        '.', '').replace('/', '').replace('-', '')

                    # Verifica se já existe este CPF nas informações adicionais
                    if not InformacaoAdicional.objects.filter(
                        caso=comunicacao.caso,
                        rif=comunicacao.rif,
                        indexador=comunicacao.indexador,
                        cpf=cpf_limpo
                    ).exists():
                        # Garantir que todos os campos obrigatórios tenham valores válidos
                        tipo_transacao_valor = detalhe.get(
                            'tipo_transacao', '') or 'N/A'
                        nome_valor = detalhe.get('nome', '') or 'N/A'
                        valor_valor = detalhe.get('valor', '') or '0'
                        quantidade_valor = detalhe.get('quantidade', '') or '0'
                        plataforma_valor = detalhe.get(
                            'plataforma', '') or 'N/A'

                        try:
                            valor_numerico = float(str(valor_valor).replace(
                                'R$', '').replace('.', '').replace(',', '.').strip())
                            if valor_numerico > 0:
                                # Cria uma nova informação adicional
                                InformacaoAdicional.objects.create(
                                    rif=comunicacao.rif,
                                    caso=comunicacao.caso,
                                    arquivo=comunicacao.arquivo,
                                    comunicacao=comunicacao,
                                    indexador=comunicacao.indexador,
                                    tipo_transacao=tipo_transacao_valor,
                                    cpf=cpf_limpo,
                                    nome=nome_valor,
                                    valor=valor_numerico,
                                    transacoes=quantidade_valor,
                                    plataforma=plataforma_valor,
                                )
                                registros_salvos += 1
                        except (ValueError, TypeError):
                            # Se houver erro na conversão do valor, ignora este registro
                            continue

                if registros_salvos > 0:
                    print(f'com {registros_salvos} registros salvos')
                    messages.success(
                        request, f'Comunicação processada com sucesso! {registros_salvos} registro(s) adicionado(s).')
                else:
                    print('sem registros salvos')
                    messages.warning(
                        request, 'Nenhum registro foi salvo. Verifique os dados da comunicação.')

            except json.JSONDecodeError as e:
                print('json inválido')
                print(f"Erro JSON original: {str(e)}")
                print(f"JSON problemático: {resposta_limpa[:500]}...")

                # Tenta extrair objetos individuais usando regex
                print("Tentando extrair objetos JSON individuais...")
                detalhes_envolvidos_json = extrair_objetos_json_individuais(
                    resposta_limpa)

                # Se a regex não funcionou bem, tenta o método de balanceamento
                if len(detalhes_envolvidos_json) == 0:
                    print(
                        "Regex não encontrou objetos, tentando balanceamento de chaves...")
                    detalhes_envolvidos_json = extrair_objetos_json_balanceamento(
                        resposta_limpa)

                if detalhes_envolvidos_json:
                    print(
                        f"Conseguiu extrair {len(detalhes_envolvidos_json)} objetos válidos")

                    # Processa os objetos válidos
                    registros_salvos = 0
                    for detalhe in detalhes_envolvidos_json:
                        cpf_cnpj = detalhe.get('cpf_cnpj', '')
                        if not cpf_cnpj:
                            continue

                        cpf_limpo = cpf_cnpj.replace(
                            '.', '').replace('/', '').replace('-', '')

                        if not InformacaoAdicional.objects.filter(
                            caso=comunicacao.caso,
                            rif=comunicacao.rif,
                            indexador=comunicacao.indexador,
                            cpf=cpf_limpo
                        ).exists():
                            # Garantir que todos os campos obrigatórios tenham valores válidos
                            tipo_transacao_valor = detalhe.get(
                                'tipo_transacao', '') or 'N/A'
                            nome_valor = detalhe.get('nome', '') or 'N/A'
                            valor_valor = detalhe.get('valor', '') or '0'
                            quantidade_valor = detalhe.get(
                                'quantidade', '') or '0'
                            plataforma_valor = detalhe.get(
                                'plataforma', '') or 'N/A'

                            try:
                                valor_numerico = float(str(valor_valor).replace(
                                    'R$', '').replace('.', '').replace(',', '.').strip())
                                if valor_numerico > 0:
                                    # Cria uma nova informação adicional
                                    InformacaoAdicional.objects.create(
                                        rif=comunicacao.rif,
                                        caso=comunicacao.caso,
                                        arquivo=comunicacao.arquivo,
                                        comunicacao=comunicacao,
                                        indexador=comunicacao.indexador,
                                        tipo_transacao=tipo_transacao_valor,
                                        cpf=cpf_limpo,
                                        nome=nome_valor,
                                        valor=valor_numerico,
                                        transacoes=quantidade_valor,
                                        plataforma=plataforma_valor,
                                    )
                                    registros_salvos += 1
                            except (ValueError, TypeError):
                                # Se houver erro na conversão do valor, ignora este registro
                                continue

                    if registros_salvos > 0:
                        messages.success(
                            request, f'Comunicação processada parcialmente! {registros_salvos} registro(s) extraído(s) de JSON malformado.')
                    else:
                        messages.warning(
                            request, 'JSON malformado e nenhum registro válido encontrado.')
                else:
                    messages.error(
                        request, f'Erro ao interpretar resposta da IA: {str(e)}')

            except Exception as e:
                print('erro geral')
                messages.error(
                    request, f'Erro ao salvar informações no banco de dados: {str(e)}')
        else:
            print('sem detalhes')
            messages.error(
                request, 'Não foi possível extrair informações do texto com a IA.')

    except Comunicacao.DoesNotExist:
        messages.error(request, 'Comunicação não encontrada.')
    except Envolvido.DoesNotExist:
        messages.error(request, 'Envolvido não encontrado.')
    except Exception as e:
        messages.error(request, f'Erro ao processar envolvido: {str(e)}')

    return redirect('financeira:financeira_errosimportacao')


@login_required
def resumo_por_id(request, caso_id):
    """Gera relatório financeiro para um caso específico"""
    try:
        # Busca o caso pelo ID
        caso = get_object_or_404(Caso, id=caso_id)

        # Buscar todos os dados relacionados ao caso
        rifs = RIF.objects.filter(caso=caso)
        comunicacoes = Comunicacao.objects.filter(caso=caso)
        envolvidos = Envolvido.objects.filter(caso=caso)
        ocorrencias = Ocorrencia.objects.filter(caso=caso)
        investigados = caso.investigados.all()
        informacoes_adicionais = InformacaoAdicional.objects.filter(caso=caso)

        # Converter RIFs para lista de dicionários
        rifs_list = []
        for rif in rifs:
            rifs_list.append({
                'id': rif.id,
                'numero': rif.numero,
                'caso': rif.caso,
                'movimentacao': moeda(sum(processar_valor_monetario(com.campo_a)
                                          for com in comunicacoes.filter(rif=rif) if com.campo_a))
            })

        # Filtra os titulares e representantes
        titulares = envolvidos.filter(tipo_envolvido='Titular').values(
            'cpf_cnpj_envolvido', 'nome_envolvido', 'tipo_envolvido', 'indexador'
        ).distinct().order_by('nome_envolvido')

        representantes = envolvidos.filter(tipo_envolvido='Representante').values(
            'cpf_cnpj_envolvido', 'nome_envolvido', 'tipo_envolvido', 'indexador'
        ).distinct().order_by('nome_envolvido')

        # Total movimentado no Caso
        movimentacao = sum(processar_valor_monetario(com.campo_a)
                           for com in comunicacoes if com.campo_a)

        # Processar dados dos titulares
        titulares_extratos = []
        for titular in titulares:
            # Filtrar comunicações do titular
            comunicacoes_titular = comunicacoes.filter(
                indexador=titular['indexador'])

            # Calcular totais do titular
            movimentacao_titular = sum(processar_valor_monetario(
                com.campo_a) for com in comunicacoes_titular if com.campo_a)
            creditos_titular = sum(processar_valor_monetario(
                com.campo_b) for com in comunicacoes_titular if com.campo_b)
            debitos_titular = sum(processar_valor_monetario(
                com.campo_c) for com in comunicacoes_titular if com.campo_c)

            # Buscar ocorrências do titular
            ocorrencias_titular = ocorrencias.filter(
                indexador=titular['indexador'])

            # Buscar informações adicionais do titular
            info_adicionais = informacoes_adicionais.filter(
                indexador=titular['indexador'])

            # Verificar se é investigado
            is_investigado = investigados.filter(
                cpf_cnpj=titular['cpf_cnpj_envolvido']).exists()

            titulares_extratos.append({
                'nome': titular['nome_envolvido'],
                'investigado': is_investigado,
                'cpf': titular['cpf_cnpj_envolvido'],
                'kyc': '',  # Será preenchido pela IA se necessário
                'movimentacao_total': moeda(movimentacao_titular),
                'creditos': moeda(creditos_titular),
                'debitos': moeda(debitos_titular),
                'comunicacoes': list(comunicacoes_titular.values()),
                'ocorrencias': list(ocorrencias_titular.values('ocorrencia')),
                'outras_informacoes': list(info_adicionais.values_list('informacoes_adicionais', flat=True)),
                'observacoes_analista': ''  # Será preenchido pela IA se necessário
            })

        # Dados para o template
        data = {
            'caso': caso,
            'rifs': rifs_list,
            'comunicacoes': comunicacoes,
            'envolvidos': envolvidos,
            'investigados': investigados,
            'titulares': titulares,
            'representantes': representantes,
            'ocorrencias': ocorrencias,
            'movimentacao': moeda(movimentacao),
            'titulares_extratos': titulares_extratos,
        }

        # Gerar o documento
        doc = DocxTemplate("templates/documentos/rif.docx")
        doc.render(data)

        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            temp_path = temp_file.name
            doc.save(temp_path)

            # Criar ZIP com o documento e os arquivos Excel
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                # Adiciona o documento Word
                zip_file.write(
                    temp_path, 'Relatorio Inteligência Financeira.docx')

                # Cria e adiciona os arquivos Excel
                if not df_rifdetalhado.empty:
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_rifdetalhado.to_excel(writer, index=False)
                    zip_file.writestr('RIF Detalhado.xlsx',
                                      excel_buffer.getvalue())

                if not df_comunicacoes.empty:
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_comunicacoes.to_excel(writer, index=False)
                    zip_file.writestr('Comunicações.xlsx',
                                      excel_buffer.getvalue())

                if not df_envolvidos.empty:
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_envolvidos.to_excel(writer, index=False)
                    zip_file.writestr('Envolvidos.xlsx',
                                      excel_buffer.getvalue())

                if not df_ocorrencias.empty:
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_ocorrencias.to_excel(writer, index=False)
                    zip_file.writestr('Ocorrências.xlsx',
                                      excel_buffer.getvalue())

                # Converte a lista de informações adicionais para DataFrame
                if todas_informacoes_adicionais:
                    df_info_adicionais = pd.DataFrame(
                        {'informacoes': todas_informacoes_adicionais})
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_info_adicionais.to_excel(writer, index=False)
                    zip_file.writestr(
                        'Informações Adicionais.xlsx', excel_buffer.getvalue())

            # Remove o arquivo temporário
            try:
                os.unlink(temp_path)
            except:
                pass

            # Enviar resposta
            response = HttpResponse(
                zip_buffer.getvalue(), content_type='application/zip')
            response[
                'Content-Disposition'] = f'attachment; filename="Relatorio Inteligência Financeira - Caso {caso.numero}.zip"'
            return response

    except Exception as e:
        messages.error(request, f'Erro ao gerar relatório: {str(e)}')
        return redirect('financeira:financeira_index')


##################################################################################################
# CHAT DE ANÁLISE FINANCEIRA
##################################################################################################
@login_required
def financeira_chat(request):
    """
    Renderiza a página de chat de análise financeira.
    """
    return render(request, 'financeira/chat.html')































@login_required
def financeira_chat_api(request):
    """
    API para interagir com o chat de análise financeira usando LLM.
    """
    print("--- [DEBUG] Iniciando financeira_chat_api ---")
    if request.method == 'POST':
        print("[DEBUG] Método é POST.")
        try:
            data = json.loads(request.body)
            user_prompt = data.get('prompt')
            print(f"[DEBUG] Prompt do usuário: {user_prompt}")

            if not user_prompt:
                print("[DEBUG] ERRO: Prompt não fornecido.")
                return JsonResponse({'error': 'Prompt não fornecido.'}, status=400)

            # 1. Obter caso ativo
            caso_ativo = Caso.objects.filter(ativo=True).first()
            if not caso_ativo:
                print("[DEBUG] ERRO: Nenhum caso ativo encontrado.")
                return JsonResponse({'error': 'Nenhum caso ativo encontrado.'}, status=400)
            print(f"[DEBUG] Caso ativo: {caso_ativo.numero}")

            # 2. Obter dados
            comunicacoes = Comunicacao.objects.filter(
                caso=caso_ativo).select_related('rif')
            envolvidos = Envolvido.objects.filter(caso=caso_ativo)
            print(f"[DEBUG] Comunicações encontradas: {comunicacoes.count()}")
            print(f"[DEBUG] Envolvidos encontrados: {envolvidos.count()}")

            # 3. Construir contexto para a LLM
            context_data = f"## Análise do Caso: {caso_ativo.numero} - {caso_ativo.descricao}\n\n"

            context_data += "### Comunicações Financeiras (RIFs) - Top 10\n"
            context_data += "| RIF | Data Operação | Valor Total | Comunicante |\n"
            context_data += "|---|---|---|---|\n"
            for com in comunicacoes[:10]:
                context_data += f"| {com.rif.numero} | {com.data_operacao} | {moeda(com.campo_a)} | {com.nome_comunicante} |\n"

            context_data += "\n### Principais Envolvidos (Top 20)\n"
            context_data += "| Nome | CPF/CNPJ | Tipo |\n"
            context_data += "|---|---|---|\n"

            nomes_vistos = set()
            envolvidos_unicos = []
            for env in envolvidos:
                if env.nome_envolvido not in nomes_vistos:
                    envolvidos_unicos.append(env)
                    nomes_vistos.add(env.nome_envolvido)
                    if len(envolvidos_unicos) >= 20:
                        break

            for env in envolvidos_unicos:
                context_data += f"| {env.nome_envolvido} | {env.cpf_cnpj_envolvido} | {env.tipo_envolvido} |\n"

            print("--- [DEBUG] Contexto para LLM ---")
            print(context_data)
            print("---------------------------------")

            # 4. Chamar a LLM
            prompt_template = _get_prompt_from_db(
                'financeira', 'chat_ia', 'Chat de Análise Financeira')
            if not prompt_template:
                print("[DEBUG] Usando prompt padrão.")
                prompt_template = """Você é um assistente especialista em análise de inteligência financeira. Sua tarefa é responder perguntas sobre dados financeiros de um caso de investigação. Use os dados fornecidos no contexto para formular sua resposta. Seja claro e objetivo.

**Contexto do Caso:**
{contexto}

**Pergunta do Usuário:**
{pergunta}
"""
            else:
                print("[DEBUG] Usando prompt do banco de dados.")

            final_prompt = prompt_template.format(
                contexto=context_data, pergunta=user_prompt)
            print("--- [DEBUG] Prompt final para LLM ---")
            print(final_prompt)
            print("-----------------------------------")

            response_text = executar_prompt([
                {"role": "user", "content": final_prompt}
            ])

            print(f"[DEBUG] Resposta da LLM: {response_text}")

            return JsonResponse({'response': response_text})

        except Exception as e:
            print(f"[DEBUG] ERRO GERAL: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e)}, status=500)

    else:
        print(f"[DEBUG] ERRO: Método não permitido: {request.method}")
        return JsonResponse({'error': 'Método não permitido'}, status=405)
























@login_required
def processar_envolvido_especifico(request, comunicacao_id, envolvido_id):
    """
    Processa um único envolvido para extrair informações adicionais usando IA.
    """
    try:
        # Buscar os objetos do banco de dados
        comunicacao = get_object_or_404(Comunicacao, id=comunicacao_id)
        envolvido = get_object_or_404(Envolvido, id=envolvido_id)

        # Verificar se já existem informações para este CPF nesta comunicação
        cpf_limpo = str(envolvido.cpf_cnpj_envolvido).replace(
            '.', '').replace('-', '').replace('/', '')
        if InformacaoAdicional.objects.filter(
            comunicacao=comunicacao,
            cpf=cpf_limpo
        ).exists():
            messages.warning(
                request, f'O envolvido {envolvido.nome_envolvido} já possui informações adicionais cadastradas para esta comunicação.')
            return redirect('financeira:financeira_errosimportacao')

        # Montar o prompt para a IA
        texto_completo = comunicacao.informacoes_adicionais
        nome_alvo = envolvido.nome_envolvido
        cpf_alvo = envolvido.cpf_cnpj_envolvido

        prompt_text = f"""No texto a seguir, extraia as informações de transações financeiras (crédito ou débito), valor e quantidade especificamente para a pessoa chamada **{nome_alvo}** com CPF/CNPJ **{cpf_alvo}**.

<texto>
{texto_completo}
</texto>

A sua resposta deve ser um objeto JSON no seguinte formato:
[{{'nome': '{nome_alvo}', 'cpf_cnpj': '{cpf_alvo}', 'tipo_transacao': 'tipo', 'valor': 'valor', 'quantidade': 'quantidade', 'plataforma': 'plataforma'}}]

Se nenhuma transação for encontrada para esta pessoa, retorne um array JSON vazio []. Não forneça nenhuma explicação, apenas o objeto JSON.
"""

        # Chamar a IA
        detalhes_envolvidos_str = executar_prompt(
            [{"role": "user", "content": prompt_text}])

        # Processar a resposta da IA
        if detalhes_envolvidos_str:
            try:
                # Limpa a resposta da IA removendo marcadores de código
                resposta_limpa = detalhes_envolvidos_str.replace(
                    '```json', '').replace('```', '').replace('`', '').strip()

                detalhes_envolvidos = json.loads(resposta_limpa)

                if not detalhes_envolvidos:
                    messages.info(
                        request, f'Nenhuma informação adicional encontrada para {nome_alvo} na comunicação.')
                    return redirect('financeira:financeira_errosimportacao')

                # Salvar no banco de dados
                registros_salvos = 0
                for detalhe in detalhes_envolvidos:
                    cpf_cnpj = detalhe.get('cpf_cnpj', '')
                    if not cpf_cnpj:
                        continue  # Pula se não há CPF/CNPJ

                    cpf_limpo = cpf_cnpj.replace(
                        '.', '').replace('/', '').replace('-', '')

                    # Verifica se já existe este CPF nas informações adicionais
                    if not InformacaoAdicional.objects.filter(
                        caso=comunicacao.caso,
                        rif=comunicacao.rif,
                        indexador=comunicacao.indexador,
                        cpf=cpf_limpo
                    ).exists():
                        # Garantir que todos os campos obrigatórios tenham valores válidos
                        tipo_transacao_valor = detalhe.get(
                            'tipo_transacao', '') or 'N/A'
                        nome_valor = detalhe.get(
                            'nome', nome_alvo) or nome_alvo
                        valor_valor = detalhe.get('valor', '') or '0'
                        quantidade_valor = detalhe.get('quantidade', '') or '0'
                        plataforma_valor = detalhe.get(
                            'plataforma', '') or 'N/A'

                        # Converter valor para float
                        try:
                            valor_numerico = float(str(valor_valor).replace('R$', '').replace('.', '').replace(',', '.'))
                        except (ValueError, TypeError):
                            valor_numerico = 0.0
                            
                        InformacaoAdicional.objects.create(
                            rif=comunicacao.rif,
                            caso=comunicacao.caso,
                            arquivo=comunicacao.arquivo,
                            comunicacao=comunicacao,
                            indexador=comunicacao.indexador,
                            tipo_transacao=tipo_transacao_valor,
                            cpf=cpf_limpo,
                            nome=nome_valor,
                            valor=valor_numerico,
                            transacoes=quantidade_valor,
                            plataforma=plataforma_valor,
                        )
                        registros_salvos += 1

                if registros_salvos > 0:
                    messages.success(
                        request, f'Informações de {nome_alvo} processadas com sucesso! {registros_salvos} registro(s) adicionado(s).')
                else:
                    messages.warning(
                        request, f'Nenhum registro foi salvo para {nome_alvo}. Verifique se o CPF/CNPJ confere.')

            except json.JSONDecodeError as e:
                print(f"Erro JSON original: {str(e)}")
                print(f"JSON problemático: {resposta_limpa[:500]}...")

                # Tenta extrair objetos individuais usando regex
                print("Tentando extrair objetos JSON individuais...")
                detalhes_envolvidos = extrair_objetos_json_individuais(
                    resposta_limpa)

                # Se a regex não funcionou bem, tenta o método de balanceamento
                if len(detalhes_envolvidos) == 0:
                    print(
                        "Regex não encontrou objetos, tentando balanceamento de chaves...")
                    detalhes_envolvidos = extrair_objetos_json_balanceamento(
                        resposta_limpa)

                if detalhes_envolvidos:
                    print(
                        f"Conseguiu extrair {len(detalhes_envolvidos)} objetos válidos")

                    # Processa os objetos válidos
                    registros_salvos = 0
                    for detalhe in detalhes_envolvidos:
                        cpf_cnpj = detalhe.get('cpf_cnpj', '')
                        if not cpf_cnpj:
                            continue

                        cpf_limpo = cpf_cnpj.replace(
                            '.', '').replace('/', '').replace('-', '')

                        if not InformacaoAdicional.objects.filter(
                            caso=comunicacao.caso,
                            rif=comunicacao.rif,
                            indexador=comunicacao.indexador,
                            cpf=cpf_limpo
                        ).exists():
                            tipo_transacao_valor = detalhe.get(
                                'tipo_transacao', '') or 'N/A'
                            nome_valor = detalhe.get(
                                'nome', nome_alvo) or nome_alvo
                            valor_valor = detalhe.get('valor', '') or '0'
                            quantidade_valor = detalhe.get(
                                'quantidade', '') or '0'
                            plataforma_valor = detalhe.get(
                                'plataforma', '') or 'N/A'

                            # Converter valor para float
                            try:
                                valor_numerico = float(str(valor_valor).replace('R$', '').replace('.', '').replace(',', '.'))
                            except (ValueError, TypeError):
                                valor_numerico = 0.0
                                
                            InformacaoAdicional.objects.create(
                                rif=comunicacao.rif,
                                caso=comunicacao.caso,
                                arquivo=comunicacao.arquivo,
                                comunicacao=comunicacao,
                                indexador=comunicacao.indexador,
                                tipo_transacao=tipo_transacao_valor,
                                cpf=cpf_limpo,
                                nome=nome_valor,
                                valor=valor_numerico,
                                transacoes=quantidade_valor,
                                plataforma=plataforma_valor,
                            )
                            registros_salvos += 1

                    if registros_salvos > 0:
                        messages.success(
                            request, f'Informações de {nome_alvo} processadas parcialmente! {registros_salvos} registro(s) extraído(s) de JSON malformado.')
                    else:
                        messages.warning(
                            request, f'JSON malformado e nenhum registro válido encontrado para {nome_alvo}.')
                else:
                    messages.error(
                        request, f'Erro ao interpretar resposta da IA: {str(e)}')

            except Exception as e:
                messages.error(
                    request, f'Erro ao salvar informações no banco de dados: {str(e)}')
        else:
            messages.error(
                request, 'Não foi possível extrair informações do texto com a IA.')

    except Comunicacao.DoesNotExist:
        messages.error(request, 'Comunicação não encontrada.')
    except Envolvido.DoesNotExist:
        messages.error(request, 'Envolvido não encontrado.')
    except Exception as e:
        messages.error(request, f'Erro ao processar envolvido: {str(e)}')

    return redirect('financeira:financeira_errosimportacao')


def extrair_objetos_json_individuais(texto):
    """
    Extrai objetos JSON individuais de um texto usando regex,
    mesmo quando o JSON completo está malformado.
    """
    import re

    # Remove quebras de linha desnecessárias e normaliza o texto
    texto_normalizado = re.sub(r'\s+', ' ', texto)

    # Padrão regex mais robusto para encontrar objetos JSON
    # Permite conteúdo aninhado e multi-linha
    padrao = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'

    objetos_encontrados = re.findall(padrao, texto_normalizado, re.DOTALL)
    objetos_validos = []

    # Se não encontrou com o padrão normalizado, tenta com texto original
    if not objetos_encontrados:
        print("Tentando com texto original...")
        objetos_encontrados = re.findall(padrao, texto, re.DOTALL)

    for i, obj_str in enumerate(objetos_encontrados):
        try:
            # Limpa e normaliza o objeto antes de fazer parse
            obj_limpo = obj_str.strip()

            # Remove vírgulas no final se existirem
            if obj_limpo.endswith(','):
                obj_limpo = obj_limpo[:-1]

            # Tenta corrigir problemas comuns de formatação
            # Remove vírgula antes de }
            obj_limpo = re.sub(r',\s*}', '}', obj_limpo)
            # Remove vírgula antes de ]
            obj_limpo = re.sub(r',\s*]', ']', obj_limpo)

            # Tenta fazer o parse do objeto individual
            obj = json.loads(obj_limpo)
            objetos_validos.append(obj)
            print(f"Objeto {i+1} válido: {obj.get('nome', 'N/A')}")
        except json.JSONDecodeError as e:
            print(f"Objeto {i+1} inválido: {str(e)[:100]}...")
            # Para debug, mostra o objeto problemático
            print(f"Conteúdo problemático: {obj_str[:200]}...")
            continue

    return objetos_validos


def processar_comunicacao_completa(comunicacao_id):
    """
    Função completa para processar uma comunicação usando IA com todas as validações.
    """
    try:
        comunicacao = get_object_or_404(Comunicacao, id=comunicacao_id)

        # Busca envolvidos sem informações adicionais
        envolvidos_sem_info = Envolvido.objects.filter(
            caso=comunicacao.caso,
            rif=comunicacao.rif,
            indexador=comunicacao.indexador
        ).exclude(
            cpf_cnpj_envolvido__in=InformacaoAdicional.objects.filter(
                caso=comunicacao.caso,
                rif=comunicacao.rif,
                indexador=comunicacao.indexador
            ).values_list('cpf', flat=True)
        )

        if not envolvidos_sem_info.exists():
            return {"success": True, "message": "Todos os envolvidos já têm informações processadas."}

        # Prepara o texto e chama a IA
        texto_completo = comunicacao.informacoes_adicionais.replace(
            '&#x0D;', '').replace('&#x0D', '')

        # Lista de nomes para focar o processamento
        nomes_sem_info = [
            env.nome_envolvido for env in envolvidos_sem_info[:20]]
        nomes_str = ", ".join(nomes_sem_info)

        # Buscar prompt do banco de dados
        prompt_text = _get_prompt_from_db(
            'financeira', 'informacoes_adicionais', 'Análise de Informações Adicionais')

        if prompt_text:
            prompt_content = prompt_text.format(texto=texto_completo)
            prompt_adicional = f"Foque nos seguintes envolvidos: {nomes_str}"
            resposta_ia = executar_prompt([
                {"role": "user", "content": prompt_content},
                {"role": "user", "content": prompt_adicional}
            ])
        else:
            resposta_ia = executar_prompt([{
                "role": "user",
                "content": f"""Extraia informações de transações financeiras do texto. Foque nos envolvidos: {nomes_str}
                
<texto>{texto_completo}</texto>

Resposta em JSON: [{{'nome': 'nome', 'cpf_cnpj': 'cpf', 'tipo_transacao': 'tipo', 'valor': 'valor', 'quantidade': 'qtd', 'plataforma': 'plataforma'}}]"""
            }])

        # Processa a resposta da IA
        objetos_extraidos = processar_resposta_ia_robusta(
            resposta_ia, comunicacao)

        if not objetos_extraidos:
            return {"success": False, "message": "Nenhum dado foi extraído da IA."}

        # Salva os dados
        registros_salvos = 0
        for detalhe in objetos_extraidos:
            if salvar_informacao_adicional_segura(comunicacao, detalhe):
                registros_salvos += 1

        return {
            "success": True,
            "message": f"Processamento concluído! {registros_salvos} registro(s) salvos de {len(objetos_extraidos)} extraídos.",
            "registros_salvos": registros_salvos,
            "total_extraidos": len(objetos_extraidos)
        }

    except Exception as e:
        return {"success": False, "message": f"Erro no processamento: {str(e)}"}


def gerar_relatorio_estatisticas_caso(caso_id):
    """
    Gera estatísticas detalhadas de um caso financeiro.
    """
    try:
        caso = get_object_or_404(Caso, id=caso_id)

        # Estatísticas básicas
        total_rifs = RIF.objects.filter(caso=caso).count()
        total_comunicacoes = Comunicacao.objects.filter(caso=caso).count()
        total_envolvidos = Envolvido.objects.filter(caso=caso).count()
        total_info_adicionais = InformacaoAdicional.objects.filter(
            caso=caso).count()

        # Envolvidos únicos por CPF
        envolvidos_unicos = Envolvido.objects.filter(
            caso=caso).values('cpf_cnpj_envolvido').distinct().count()

        # Taxa de processamento
        if total_envolvidos > 0:
            taxa_processamento = (
                total_info_adicionais / total_envolvidos) * 100
        else:
            taxa_processamento = 0

        # Valores financeiros
        comunicacoes = Comunicacao.objects.filter(caso=caso)
        valor_total = sum(processar_valor_monetario(com.campo_a)
                          for com in comunicacoes if com.campo_a)

        # Top 10 envolvidos por valor
        info_adicionais = InformacaoAdicional.objects.filter(
            caso=caso).order_by('-valor')[:10]
        top_envolvidos = [
            {
                "nome": info.nome,
                "cpf": info.cpf,
                "valor": moeda(info.valor),
                "transacoes": info.transacoes,
                "plataforma": info.plataforma
            }
            for info in info_adicionais
        ]

        return {
            "caso": caso.numero,
            "estatisticas": {
                "total_rifs": total_rifs,
                "total_comunicacoes": total_comunicacoes,
                "total_envolvidos": total_envolvidos,
                "envolvidos_unicos": envolvidos_unicos,
                "total_info_adicionais": total_info_adicionais,
                "taxa_processamento": round(taxa_processamento, 2),
                "valor_total": moeda(valor_total)
            },
            "top_envolvidos": top_envolvidos
        }

    except Exception as e:
        return {"erro": str(e)}


@login_required
def informacoes_adicionais_delete(request, info_id):
    """
    Exclui uma informação adicional específica.
    """
    try:
        info_adicional = get_object_or_404(InformacaoAdicional, id=info_id)

        # Verifica se o usuário tem permissão (se pertence ao caso ativo)
        caso_ativo = Caso.objects.filter(ativo=True).first()
        if not caso_ativo or info_adicional.caso != caso_ativo:
            messages.error(
                request, 'Você não tem permissão para excluir esta informação.')
            return redirect('financeira:financeira_informacoesadicionais')

        # Salva informações para a mensagem de confirmação
        nome_envolvido = info_adicional.nome
        valor_excluido = moeda(info_adicional.valor)

        # Exclui a informação adicional
        info_adicional.delete()

        messages.success(
            request, f'Informação de {nome_envolvido} (valor: {valor_excluido}) excluída com sucesso!')

    except InformacaoAdicional.DoesNotExist:
        messages.error(request, 'Informação adicional não encontrada.')
    except Exception as e:
        messages.error(
            request, f'Erro ao excluir informação adicional: {str(e)}')

    return redirect('financeira:financeira_informacoesadicionais')



##################################################################################################
# UPLOAD DE PLANILHA PARA INFORMACOES ADICIONAIS
##################################################################################################
@login_required
def upload_planilha(request):
    """
    Endpoint para upload de planilha contendo dados para inserir na tabela informacoes_adicionais.
    Recebe comunicacao_id e indexador via formulário e processa os dados da planilha.
    """
    if request.method == 'GET':
        # Busca o caso ativo
        caso_ativo = Caso.objects.filter(ativo=True).first()
        if not caso_ativo:
            messages.error(request, 'Nenhum caso ativo encontrado.')
            return redirect('casos')

        # Busca comunicações disponíveis para o dropdown
        comunicacoes = Comunicacao.objects.filter(
            caso=caso_ativo).select_related('rif').order_by('-id')

        context = {
            'caso': caso_ativo,
            'comunicacoes': comunicacoes,
        }
        return render(request, 'financeira/upload_planilha.html', context)

    elif request.method == 'POST':
        try:
            # Busca o caso ativo
            caso_ativo = Caso.objects.filter(ativo=True).first()
            if not caso_ativo:
                return JsonResponse({
                    'success': False,
                    'message': 'Nenhum caso ativo encontrado.'
                }, status=400)

            # Valida parâmetros obrigatórios
            comunicacao_id = request.POST.get('comunicacao_id')
            indexador = request.POST.get('indexador')
            arquivo_planilha = request.FILES.get('planilha')

            if not all([comunicacao_id, indexador, arquivo_planilha]):
                return JsonResponse({
                    'success': False,
                    'message': 'Comunicação, indexador e arquivo são obrigatórios.'
                }, status=400)

            # Busca a comunicação
            try:
                comunicacao = Comunicacao.objects.get(
                    id=comunicacao_id, caso=caso_ativo)
            except Comunicacao.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Comunicação não encontrada.'
                }, status=404)

            # Valida o indexador
            try:
                indexador_int = int(indexador)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Indexador deve ser um número válido.'
                }, status=400)

            # Lê o arquivo da planilha
            try:
                df = ler_arquivo_planilha(arquivo_planilha)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Erro ao ler planilha: {str(e)}'
                }, status=400)

            # Valida colunas obrigatórias
            colunas_obrigatorias = [
                'nome', 'cpf_cnpj', 'tipo_transacao', 'valor', 'transacoes', 'plataforma']
            colunas_encontradas = list(df.columns)
            colunas_faltantes = [
                col for col in colunas_obrigatorias if col not in df.columns]

            if colunas_faltantes:
                return JsonResponse({
                    'success': False,
                    'message': f'Colunas obrigatórias não encontradas!\n\nColunas encontradas: {", ".join(colunas_encontradas)}\n\nColunas obrigatórias faltantes: {", ".join(colunas_faltantes)}\n\nVerifique se os nomes das colunas estão exatamente como esperado (sem espaços extras, acentos, etc.)'
                }, status=400)

            # Processa e salva os dados
            registros_salvos = 0
            registros_erro = 0
            erros_detalhes = []

            for index, row in df.iterrows():
                try:
                    # Limpa e valida CPF/CNPJ
                    cpf_cnpj_original = str(row['cpf_cnpj'])
                    cpf_limpo = validar_e_limpar_cpf_cnpj(cpf_cnpj_original)

                    if not cpf_limpo:
                        erros_detalhes.append(
                            f'Linha {index + 2}: CPF/CNPJ inválido: {cpf_cnpj_original}')
                        registros_erro += 1
                        continue

                    # Limpa e valida campos obrigatórios
                    nome = str(row['nome']).strip() if pd.notna(
                        row['nome']) else ''
                    tipo_transacao = str(row['tipo_transacao']).strip(
                    ) if pd.notna(row['tipo_transacao']) else ''
                    transacoes = str(row['transacoes']).strip(
                    ) if pd.notna(row['transacoes']) else '0'
                    plataforma = str(row['plataforma']).strip(
                    ) if pd.notna(row['plataforma']) else ''

                    # Processa valor monetário
                    valor_original = str(row['valor']) if pd.notna(
                        row['valor']) else '0'
                    valor_numerico = processar_valor_monetario(valor_original)

                    # Valida campos obrigatórios
                    if not nome:
                        erros_detalhes.append(
                            f'Linha {index + 2}: Nome é obrigatório')
                        registros_erro += 1
                        continue

                    if not tipo_transacao:
                        erros_detalhes.append(
                            f'Linha {index + 2}: Tipo de transação é obrigatório')
                        registros_erro += 1
                        continue

                    if valor_numerico <= 0:
                        erros_detalhes.append(
                            f'Linha {index + 2}: Valor deve ser maior que zero: {valor_original}')
                        registros_erro += 1
                        continue

                    # Busca um arquivo relacionado à comunicação ou cria um genérico
                    arquivo = comunicacao.arquivo

                    # Verifica se já existe informação para este CPF no mesmo contexto
                    if InformacaoAdicional.objects.filter(
                        caso=caso_ativo,
                        comunicacao=comunicacao,
                        indexador=indexador_int,
                        cpf=cpf_limpo,
                        valor=valor_numerico,
                        tipo_transacao=tipo_transacao,
                    ).exists():
                        erros_detalhes.append(
                            f'Linha {index + 2}: CPF {cpf_limpo} já cadastrado para esta comunicação/indexador')
                        registros_erro += 1
                        continue

                    # Cria o registro
                    InformacaoAdicional.objects.create(
                        rif=comunicacao.rif,
                        caso=caso_ativo,
                        arquivo=arquivo,
                        comunicacao=comunicacao,
                        indexador=indexador_int,
                        tipo_transacao=tipo_transacao,
                        cpf=cpf_limpo,
                        nome=nome,
                        valor=valor_numerico,
                        transacoes=transacoes,
                        plataforma=plataforma,
                    )

                    registros_salvos += 1

                except Exception as e:
                    erros_detalhes.append(
                        f'Linha {index + 2}: Erro ao processar: {str(e)}')
                    registros_erro += 1
                    continue

            # Monta resposta
            total_registros = len(df)
            message_parts = [
                f'Upload concluído! {registros_salvos} de {total_registros} registros salvos com sucesso.']

            if registros_erro > 0:
                message_parts.append(f'{registros_erro} registros com erro.')
                if len(erros_detalhes) <= 10:  # Mostra até 10 erros
                    message_parts.extend(erros_detalhes)
                else:
                    message_parts.extend(erros_detalhes[:10])
                    message_parts.append(
                        f'... e mais {len(erros_detalhes) - 10} erros.')

            response_data = {
                'success': True,
                'message': '\n'.join(message_parts),
                'registros_salvos': registros_salvos,
                'registros_erro': registros_erro,
                'total_registros': total_registros
            }

            if registros_erro > 0:
                response_data['erros_detalhes'] = erros_detalhes

            return JsonResponse(response_data)

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }, status=500)

    else:
        return JsonResponse({
            'success': False,
            'message': 'Método não permitido'
        }, status=405)


def ler_arquivo_planilha(uploaded_file):
    """
    Lê um arquivo de planilha (Excel ou CSV) e retorna um DataFrame.
    """
    ext = os.path.splitext(uploaded_file.name)[-1].lower()

    # Salva o arquivo temporariamente
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(tmp_path)
        elif ext == '.csv':
            # Tenta diferentes encodings e delimitadores
            encodings = ['utf-8-sig', 'utf-8',
                         'windows-1252', 'latin-1', 'iso-8859-1']
            df = None

            for encoding in encodings:
                try:
                    # Detecta o delimitador primeiro
                    try:
                        with open(tmp_path, 'r', encoding=encoding, errors='ignore') as file:
                            sample = file.read(1024)
                            if sample.count(',') > sample.count(';'):
                                delimiter = ','
                            elif sample.count(';') > sample.count(','):
                                delimiter = ';'
                            else:
                                delimiter = ','
                    except:
                        delimiter = ','

                    print(
                        f"DEBUG - Tentando encoding: {encoding}, delimiter: '{delimiter}'")

                    # Tenta ler com o delimitador detectado
                    df = pd.read_csv(tmp_path, encoding=encoding,
                                     delimiter=delimiter, skipinitialspace=True)

                    # Verifica se a leitura foi bem-sucedida (mais de uma coluna)
                    if len(df.columns) > 1:
                        print(
                            f"DEBUG - Sucesso com encoding: {encoding}, delimiter: '{delimiter}'")
                        print(
                            f"DEBUG - Colunas detectadas: {list(df.columns)}")
                        break
                    else:
                        print(
                            f"DEBUG - Apenas 1 coluna detectada, tentando outros delimitadores...")
                        # Se só tem uma coluna, tenta outros delimitadores
                        for test_delimiter in [';', '\t', '|']:
                            try:
                                df_test = pd.read_csv(
                                    tmp_path, encoding=encoding, delimiter=test_delimiter, skipinitialspace=True)
                                if len(df_test.columns) > 1:
                                    df = df_test
                                    print(
                                        f"DEBUG - Sucesso com delimiter alternativo: '{test_delimiter}'")
                                    break
                            except:
                                continue
                        if len(df.columns) > 1:
                            break
                except Exception as e:
                    print(f"DEBUG - Erro com encoding {encoding}: {str(e)}")
                    continue

            if df is None or len(df.columns) <= 1:
                raise ValueError(
                    'Não foi possível ler o arquivo CSV. Verifique se está no formato correto com delimitadores adequados (vírgula ou ponto-e-vírgula).')
        else:
            raise ValueError(
                'Formato de arquivo não suportado. Use .xlsx, .xls ou .csv')

        # Debug: Mostra informações antes da normalização
        print(f"DEBUG - Colunas antes da normalização: {list(df.columns)}")

        # Limpa espaços dos nomes das colunas
        df.columns = df.columns.str.strip()

        # Remove linhas completamente vazias
        df = df.dropna(how='all')

        # Normaliza nomes das colunas (remove acentos, espaços extras, converte para lowercase)
        df.columns = df.columns.str.lower().str.strip()
        # Substitui espaços por underscore
        df.columns = df.columns.str.replace(' ', '_')
        df.columns = df.columns.str.replace(r'[àáâãäå]', 'a', regex=True)
        df.columns = df.columns.str.replace(r'[èéêë]', 'e', regex=True)
        df.columns = df.columns.str.replace(r'[ìíîï]', 'i', regex=True)
        df.columns = df.columns.str.replace(r'[òóôõö]', 'o', regex=True)
        df.columns = df.columns.str.replace(r'[ùúûü]', 'u', regex=True)
        df.columns = df.columns.str.replace(r'[ç]', 'c', regex=True)
        df.columns = df.columns.str.replace(
            r'[^a-z0-9_]', '', regex=True)  # Remove caracteres especiais

        # Debug: Mostra informações após normalização básica
        print(f"DEBUG - Colunas após normalização básica: {list(df.columns)}")

        # Mapeamento de colunas comuns que podem aparecer com nomes diferentes
        mapeamento_colunas = {
            'nome_completo': 'nome',
            'nome_pessoa': 'nome',
            'nome_envolvido': 'nome',
            'cpf': 'cpf_cnpj',
            'cnpj': 'cpf_cnpj',
            'cpf_cnpj_envolvido': 'cpf_cnpj',
            'documento': 'cpf_cnpj',
            'tipo_operacao': 'tipo_transacao',
            'tipo': 'tipo_transacao',
            'operacao': 'tipo_transacao',
            'valor_transacao': 'valor',
            'valor_operacao': 'valor',
            'montante': 'valor',
            'quantidade_transacoes': 'transacoes',
            'qtd_transacoes': 'transacoes',
            'quantidade': 'transacoes',
            'qtd': 'transacoes',
            'meio_pagamento': 'plataforma',
            'forma_pagamento': 'plataforma',
            'canal': 'plataforma',
            'origem': 'plataforma'
        }

        # Aplica o mapeamento
        df = df.rename(columns=mapeamento_colunas)

        # Debug: Mostra informações finais
        print(f"DEBUG - Colunas finais após mapeamento: {list(df.columns)}")

        return df

    finally:
        # Remove o arquivo temporário
        try:
            os.unlink(tmp_path)
        except:
            pass


@login_required
def download_modelo_planilha(request):
    """
    Gera e envia um arquivo CSV de exemplo para upload de informações adicionais.
    """
    # Cria o conteúdo do CSV de exemplo
    exemplo_csv = """nome,cpf_cnpj,tipo_transacao,valor,transacoes,plataforma
João da Silva,123.456.789-10,crédito,R$ 1.500,1,PIX
Maria Santos,98765432100,débito,2500.50,2,Transferência
Empresa ABC LTDA,12.345.678/0001-90,crédito,10000,1,Depósito
José Silva,11122233344,crédito,850.75,1,PIX
Ana Costa,55566677788,débito,1200,3,Transferência
Pedro Oliveira,99988877766,crédito,5000.00,1,Depósito"""

    # Cria a resposta HTTP com o arquivo CSV
    response = HttpResponse(
        exemplo_csv, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="modelo_informacoes_adicionais.csv"'

    # Adiciona BOM para UTF-8 para melhor compatibilidade com Excel
    response.write('\ufeff')
    response.content = '\ufeff'.encode('utf-8') + exemplo_csv.encode('utf-8')

    return response


def execute_custom_query(query):
    """
    Executa uma query SQL customizada diretamente no banco de dados
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            return pd.DataFrame(results, columns=columns)
    except Exception as e:
        print(f"Erro ao executar query: {query}")
        print(f"Erro: {e}")
        return pd.DataFrame()

def get_custom_queries_results(custom_queries = None):
    """
    Executa um conjunto de queries customizadas e retorna os resultados
    """
    if custom_queries is None:
        custom_queries = [
            {
                'name': 'Comunicações com campo_a > 10000',
                'query': "SELECT * FROM financeira_comunicacao WHERE CAST(campo_a AS REAL) > 10000"
            },
            {
                'name': 'Total de comunicações',
                'query': "SELECT COUNT(*) as total_comunicacoes FROM financeira_comunicacao"
            },
            {
                'name': 'Comunicantes distintos',
                'query': "SELECT DISTINCT nome_comunicante FROM financeira_comunicacao WHERE nome_comunicante IS NOT NULL"
            },
            {
                'name': 'Top 10 comunicantes por volume',
                'query': """
                    SELECT nome_comunicante, COUNT(*) as total_comunicacoes 
                    FROM financeira_comunicacao 
                    WHERE nome_comunicante IS NOT NULL 
                    GROUP BY nome_comunicante 
                    ORDER BY total_comunicacoes DESC 
                    LIMIT 10
                """
            }
        ]
    
    try:
        results = []
        for query_info in custom_queries:
            try:
                
                # PROTEJE O BANCO PARA SQL_INJECTIONS
                bad_words = ['DELETE', 'UPDATE', 'INSERT', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'RENAME', 'REINDEX', 'RELOAD', 'RESTART', 'RESTORE']
                for bad_word in bad_words:
                    if bad_word in query_info['query']:
                        raise Exception(f'{bad_word} não é permitido')
                
                df = execute_custom_query(query_info['query'])
                results.append({
                    'name': query_info['name'],
                    'query': query_info['query'],
                    'resultado': df.to_dict('records'),
                    'total_registros': len(df),
                    'colunas': list(df.columns) if not df.empty else []
                })
                print(f"Query executada: {query_info['name']} - {len(df)} registros")
            except Exception as e:
                results.append({
                    'name': query_info['name'],
                    'query': query_info['query'],
                    'resultado': [],
                    'total_registros': 0,
                    'colunas': [],
                    'erro': str(e)
                })
                print(f"Erro ao executar query: {query_info['name']} - {e}")
        
        return results
    except Exception as e:
        print(f"Erro ao executar queries customizadas: {e}")
        return []


@csrf_exempt
@login_required
def execute_custom_query_api(request):
    """
    API para executar queries customizadas
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query')
            
            if not query:
                return JsonResponse({'error': 'Query não fornecida'}, status=400)
            
            # Executa a query
            df = execute_custom_query(query)
            
            return JsonResponse({
                'success': True,
                'resultado': df.to_dict('records'),
                'total_registros': len(df),
                'colunas': list(df.columns) if not df.empty else []
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)

@csrf_exempt
@login_required
def create_query_api(request):
    """
    API para criar queries usando IA
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_request = data.get('request', '')
            table_name = data.get('table', '')
            
            if not user_request:
                return JsonResponse({'error': 'Descrição da query não fornecida'}, status=400)
            
            # Obter estrutura da tabela
            table_structure = get_table_structure(table_name) if table_name else get_all_tables_structure()
            
            # Criar prompt para IA
            prompt_text = create_query_prompt(user_request, table_structure)
            
            # Executar IA - converter para formato correto
            from utils.ia import executar_prompt
            # Criar o formato correto para a API
            messages = [
                {
                    "role": "user",
                    "content": prompt_text
                }
            ]
            ai_response = executar_prompt(messages)
            
            if ai_response:
                # Extrair a query SQL da resposta da IA
                sql_query = extract_sql_from_response(ai_response)
                
                # Proteção contra SQL injection
                bad_words = ['DELETE', 'UPDATE', 'INSERT', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'RENAME', 'REINDEX', 'RELOAD', 'RESTART', 'RESTORE']
                for bad_word in bad_words:
                    if bad_word.upper() in sql_query.upper():
                        return JsonResponse({
                            'success': False,
                            'error': f'Operação {bad_word} não é permitida por segurança'
                        }, status=400)
                
                return JsonResponse({
                    'success': True,
                    'query': sql_query,
                    'ai_response': ai_response
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Erro ao gerar query com IA'
                }, status=500)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)
    """
    API para executar queries customizadas
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query')
            
            if not query:
                return JsonResponse({'error': 'Query não fornecida'}, status=400)
            
            # Executa a query
            df = execute_custom_query(query)
            
            return JsonResponse({
                'success': True,
                'resultado': df.to_dict('records'),
                'total_registros': len(df),
                'colunas': list(df.columns) if not df.empty else []
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Método não permitido'}, status=405)

@login_required
def custom_queries_dashboard(request):
    """
    Dashboard para visualizar resultados de queries customizadas
    """
    results = get_custom_queries_results()
    
    # Lista todas as tabelas do banco de dados que comecam com bancaria_ ou financeira_
    tables = [table for table in connection.introspection.table_names() if table.startswith('bancaria_') or table.startswith('financeira_')]
    
    context = {
        'queries_results': results,
        'total_queries': len(results),
        'successful_queries': len([r for r in results if 'erro' not in r]),
        'tables': tables
    }
    
    return render(request, 'financeira/custom_queries_dashboard.html', context)

def get_table_structure(table_name):
    """
    Obtém a estrutura de uma tabela específica
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            structure = {
                'table_name': table_name,
                'columns': []
            }
            
            for col in columns:
                structure['columns'].append({
                    'name': col[1],
                    'type': col[2],
                    'not_null': col[3],
                    'default': col[4],
                    'primary_key': col[5]
                })
            
            return structure
    except Exception as e:
        print(f"Erro ao obter estrutura da tabela {table_name}: {e}")
        return None

def get_all_tables_structure():
    """
    Obtém a estrutura de todas as tabelas financeira_ e bancaria_
    """
    tables = [table for table in connection.introspection.table_names() 
              if table.startswith('bancaria_') or table.startswith('financeira_')]
    
    structures = []
    for table in tables:
        structure = get_table_structure(table)
        if structure:
            structures.append(structure)
    
    return structures

def create_query_prompt(user_request, table_structure):
    """
    Cria um prompt para a IA gerar uma query SQL
    """
    if isinstance(table_structure, list):
        # Múltiplas tabelas
        tables_info = "\n\n".join([
            f"Tabela: {table['table_name']}\n" +
            "Colunas:\n" +
            "\n".join([f"  - {col['name']} ({col['type']})" for col in table['columns']])
            for table in table_structure
        ])
    else:
        # Uma tabela específica
        tables_info = f"Tabela: {table_structure['table_name']}\n" + \
                     "Colunas:\n" + \
                     "\n".join([f"  - {col['name']} ({col['type']})" for col in table_structure['columns']])
    
    
    prompt = f"""
Você é um especialista em SQL. Com base na estrutura do banco de dados fornecida, crie uma query SQL que atenda à solicitação do usuário.

ESTRUTURA DO BANCO DE DADOS:
{tables_info}

SOLICITAÇÃO DO USUÁRIO:
{user_request}

INSTRUÇÕES:
1. Analise a estrutura das tabelas fornecidas
2. Crie uma query SQL válida que atenda à solicitação
3. Use apenas as tabelas e colunas disponíveis
4. Se necessário, use JOINs para conectar tabelas relacionadas
5. Retorne APENAS a query SQL, sem explicações adicionais
6. Use SQLite como dialeto SQL
7. Se a solicitação não for clara, faça suposições razoáveis

QUERY SQL:
"""
    
    return prompt

def extract_sql_from_response(ai_response):
    """
    Extrai a query SQL da resposta da IA
    """
    if not ai_response:
        return ""
    
    # Remove possíveis explicações e mantém apenas a query
    lines = ai_response.strip().split('\n')
    sql_lines = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#') and not line.startswith('--') and not line.startswith('/*'):
            sql_lines.append(line)
    
    # Junta as linhas e remove possíveis prefixos
    sql_query = ' '.join(sql_lines)
    
    # Remove possíveis prefixos como "SELECT", "Query:", etc.
    sql_query = sql_query.replace('Query:', '').replace('SQL:', '').strip()
    
    # Garante que começa com SELECT
    if not sql_query.upper().startswith('SELECT'):
        # Procura por SELECT na resposta
        import re
        select_match = re.search(r'SELECT.*?(?:;|$)', ai_response, re.IGNORECASE | re.DOTALL)
        if select_match:
            sql_query = select_match.group(0).strip()
    
    return sql_query
