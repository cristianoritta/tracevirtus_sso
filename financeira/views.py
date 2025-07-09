from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum, FloatField
from django.utils import timezone
from datetime import timedelta
from .models import RIF, Comunicacao, Envolvido, Ocorrencia, InformacaoAdicional, KYC, ComunicacaoNaoProcessada
from app.models import Caso, Arquivo
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
import pandas as pd
import sqlite3
import os
import tempfile
import locale
from app.functions import sha256_dataframe
from utils.ia import executar_prompt
from django.views.decorators.http import require_GET
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from django.template.loader import render_to_string
from django.db.models.functions import Cast
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
import zipfile
from io import BytesIO
from utils.moeda import moeda, valor
import json

@login_required
def financeira_index(request):

    # Testa se tem um caso ativo.
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')

    # Calcular estatísticas
    rifs = RIF.objects.select_related('caso').order_by('-created_at')
    # Incluir em rif o numero de comunicacoes e envolvidos de cada rif
    for rif in rifs:
        rif.total_comunicacoes = Comunicacao.objects.filter(rif=rif).count()
        rif.total_envolvidos = Envolvido.objects.filter(rif=rif).count()
    
    total_rifs = rifs.count()
    total_comunicacoes = Comunicacao.objects.count()
    total_envolvidos = Envolvido.objects.count()
    total_ocorrencias = Ocorrencia.objects.count()

    # Dados dos últimos 30 dias
    comunicacoes = Comunicacao.objects.count()

    # Taxa de processamento (comunicações processadas vs não processadas)
    comunicacoes_nao_processadas = ComunicacaoNaoProcessada.objects.count()
    if total_comunicacoes > 0:
        taxa_processamento = (
            (total_comunicacoes - comunicacoes_nao_processadas) / total_comunicacoes) * 100
    else:
        taxa_processamento = 0
    
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
            valor_a = str(comunicacao.campo_a).replace('R$', '').strip()
            valor_b = str(comunicacao.campo_b).replace('R$', '').strip()
            valor_c = str(comunicacao.campo_c).replace('R$', '').strip()
            
            # Converte do formato brasileiro para float
            comunicacao.campo_a = float(valor_a.replace('.', '').replace(',', '.'))
            comunicacao.campo_b = float(valor_b.replace('.', '').replace(',', '.'))
            comunicacao.campo_c = float(valor_c.replace('.', '').replace(',', '.'))
            
            # Adiciona o valor do campo_a à lista para o gráfico
            valores_campo_a.append(comunicacao.campo_a)
            
            somas['total_a'] += comunicacao.campo_a
            somas['total_b'] += comunicacao.campo_b
            somas['total_c'] += comunicacao.campo_c

            # Adiciona o valor ao titular correspondente
            titular = Envolvido.objects.filter(indexador=comunicacao.indexador, tipo_envolvido='Titular').first()
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
    valores_por_titular_list = [{'titular': k, 'valor': float(v)} for k, v in valores_por_titular.items()]
    
    context = {
        'total_rifs': total_rifs,
        'total_comunicacoes': total_comunicacoes,
        'total_envolvidos': total_envolvidos,
        'total_ocorrencias': total_ocorrencias,
        'taxa_processamento': round(taxa_processamento, 2),
        'rifs': rifs,
        'somas': somas,
        'valores_campo_a': valores_campo_a,  # Adiciona os valores para o gráfico
        'valores_por_titular': json.dumps(valores_por_titular_list),  # Serializa para JSON
    }

    return render(request, 'financeira/index.html', context)


@login_required
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
            if RIF.objects.filter(numero=numero).exists():
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


@login_required
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


@login_required
def financeira_comunicacoes(request):
    # Busca o caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')

    # Busca todas as comunicações do caso ativo, incluindo o número do RIF
    comunicacoes = Comunicacao.objects.filter(
        caso_id=caso_ativo.id).select_related('rif')

    context = {
        'comunicacoes': comunicacoes,
        'caso': caso_ativo,
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


@login_required
def financeira_ocorrencias(request):
    # Busca o caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')

    # Busca todas as ocorrências do caso ativo, incluindo o número do RIF
    ocorrencias = Ocorrencia.objects.filter(
        caso_id=caso_ativo.id).select_related('rif')

    context = {
        'ocorrencias': ocorrencias,
        'caso': caso_ativo,
    }
    return render(request, 'financeira/ocorrencias.html', context)


@login_required
def ocorrencia_ajuda(request, id):
    ocorrencia = Ocorrencia.objects.get(id=id)

    titular = Envolvido.objects.filter(
        caso_id=ocorrencia.caso_id, tipo_envolvido='Titular', indexador=ocorrencia.indexador).first()
    print(titular)

    # Executar uma IA para gerar uma ajuda para a ocorrência
    ajuda = executar_prompt([{
        "role": "user",
        "content": f"Você é um especialista em investigação financeira e lavagem de dinheiro. Explique o que significa na prática, e com exemplos, essas tipificacoes da Lavagem do Dinheiro informadas pelo COAF: {ocorrencia.ocorrencia}. O nome do titular é {titular.nome_envolvido}, o CPF/CNPJ é {titular.cpf_cnpj_envolvido}, a agência é {titular.agencia_envolvido} e a conta é {titular.conta_envolvido}."
    }])

    # Retorna a ajuda em formato markdown
    return HttpResponse(ajuda, content_type="text/markdown; charset=utf-8")


@login_required
def financeira_informacoesadicionais(request):
    # Busca o caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')

    # Busca as informações adicionais do caso ativo
    informacoes_adicionais = InformacaoAdicional.objects.filter(caso=caso_ativo).order_by('indexador', 'nome')
    
    if not informacoes_adicionais:
        
        # Seleciona o campo informacao_adicional da tabela comunicacao
        informacoes_adicionais = []
        comunicacoes = Comunicacao.objects.filter(caso=caso_ativo)
        for com  in comunicacoes:
            informacoes_adicionais.append(com.informacoes_adicionais)
            
            # Processa as informações adicionais com IA
            detalhes_envolvidos = executar_prompt([{
                "role": "user",
                "content": f"""Você é um especialista em investigação financeira e lavagem de dinheiro. Identifique, no texto, os envolvidos (nome e cpf/cnpj) o tipo de transação (crédito, débito) o valor (R$) e a quantidade. O Campo plataforma pode ser 'PIX', 'Depósito', 'Transferência' ou outras referência que você encontrar - se não encontrar algo explicito, deixe em branco. <texto>{informacoes_adicionais}</texto>. 
                ATENÇÃO. A sua resposta deve ser um objeto json [{{'nome': 'nome', 'cpf_cnpj': 'cpf/cnpj', 'tipo_transacao': 'tipo', 'valor': 'valor', 'quantidade': 'quantidade', 'plataforma': ''}}]. Não de nenhuma explicação, apenas o objeto json. """
            }])
            
            if detalhes_envolvidos:
                detalhes_envolvidos = json.loads(detalhes_envolvidos.replace('json', '').replace('`', ''))
                
                # Salva no banco de dados
                for detalhe in detalhes_envolvidos:
                    # Cria uma nova informação adicional
                    InformacaoAdicional.objects.create(
                        rif=com.rif,
                        caso=caso_ativo,
                        arquivo=com.arquivo,
                        comunicacao=com,
                        indexador=com.indexador,
                        tipo_transacao=detalhe['tipo_transacao'],
                        cpf=detalhe['cpf_cnpj'],
                        nome=detalhe['nome'],
                        valor=valor(detalhe['valor']),
                        transacoes=detalhe['quantidade'],
                        plataforma=detalhe['plataforma'],
                    )
            
                break
    else:
        detalhes_envolvidos = informacoes_adicionais

    # Arruma a coluna Valor para moeda(), mantendo as outras colunas
    detalhes_envolvidos = [{**detalhe, 'valor': moeda(detalhe['valor'])} if isinstance(detalhe, dict) else {**model_to_dict(detalhe), 'valor': moeda(detalhe.valor)} for detalhe in detalhes_envolvidos]
            
        
    context = {
        'caso': caso_ativo,
        'informacoes_adicionais': detalhes_envolvidos,
    }
    return render(request, 'financeira/informacoes_adicionais.html', context)


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
def financeira_dashboard(request):
    return render(request, 'financeira/dashboard.html')


@login_required
def financeira_errosimportacao(request):
    return render(request, 'financeira/errosimportacao.html')


@login_required
def listar_rifs(request):
    """Retorna uma lista de RIFs em formato JSON para o modal de importação"""
    rifs = RIF.objects.select_related('caso').order_by('-created_at')
    rifs_list = [{'id': rif.id, 'numero': rif.numero} for rif in rifs]
    return JsonResponse(rifs_list, safe=False)


@login_required
def importar_arquivos(request):
    """Importa os arquivos de comunicações, envolvidos e ocorrências para uma RIF"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Método não permitido'
        }, status=405)

    # Validar se a RIF foi selecionada
    rif_id = request.POST.get('rif')
    if not rif_id:
        return JsonResponse({
            'success': False,
            'errors': {
                'rif': ['Selecione uma RIF']
            }
        }, status=400)

    try:
        rif = RIF.objects.get(id=rif_id)
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

                # Processa campos específicos
                print(f'Vai salvar o dataframe na tabela {tipo}')

                if tipo == 'comunicacoes':
                    # Processa informações adicionais

                    df.to_sql('financeira_comunicacao', con=conn,
                              if_exists='append', index=False)
                    resultado['comunicacoes'] = len(df)

                elif tipo == 'envolvidos':
                    # Formata CPF/CNPJ
                    df['cpf_cnpj_envolvido'] = df['cpf_cnpj_envolvido'].str.replace(
                        r'\D', '', regex=True)

                    df.to_sql('financeira_envolvido', con=conn,
                              if_exists='append', index=False)
                    resultado['envolvidos'] = len(df)

                elif tipo == 'ocorrencias':

                    df.to_sql('financeira_ocorrencia', con=conn,
                              if_exists='append', index=False)
                    resultado['ocorrencias'] = len(df)

                print(resultado)

            except Exception as e:
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
    if isinstance(valor, (int, float)):
        return valor  # Retorna diretamente se já for numérico

    if str(valor).count(',') > 0:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

        valor = locale.atof(valor)

    if valor == '':
        valor = 0

    return float(valor)

# Calcular totais
def parse_valor(valor):
    if not valor:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    valor = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(valor)
    except Exception:
        return 0.0

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

        #
        # SALVA NO BANCO DE DADOS
        #
        conn = sqlite3.connect('db.sqlite3')
        print(f'Salvando o dataframe na tabela {table_name}')
        df.to_sql(table_name, con=conn, if_exists='append', index=False)

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

    return df


@require_GET
def envolvido_detalhes(request, cpf_cnpj):
    # Busca o envolvido principal
    envolvido = Envolvido.objects.filter(cpf_cnpj_envolvido=cpf_cnpj).first()
    
    if not envolvido:
        messages.error(request, 'Envolvido não encontrado.')
        return redirect('financeira:financeira_envolvidos')
    
    # Busca todas as comunicações relacionadas ao envolvido
    comunicacoes = Comunicacao.objects.filter(
        rif=envolvido.rif,
        indexador=envolvido.indexador
    )
    
    context = {
        'envolvido': envolvido,
        'comunicacoes': comunicacoes,
        'rif': envolvido.rif
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
        
        # Buscar o envolvido
        envolvido = get_object_or_404(Envolvido, cpf_cnpj_envolvido=cpf_cnpj_envolvido, rif=rif)
        
        # Buscar todas as comunicações relacionadas ao envolvido (mesmo indexador)
        comunicacoes = Comunicacao.objects.filter(
            rif__caso=rif.caso,
            indexador=envolvido.indexador
        ).order_by('-data_recebimento')
        
        context = {
            'envolvido': envolvido,
            'rif': rif,
            'comunicacoes': comunicacoes,
            'caso': rif.caso
        }
        
        return render(request, 'financeira/comunicacoes_envolvido.html', context)
        
    except Exception as e:
        messages.error(request, f'Erro ao buscar comunicações: {str(e)}')
        return redirect('financeira:financeira_envolvidos')


@login_required(login_url='/login')
def relatorio(request):
    """Gera relatório financeiro do caso"""
    
    # Testa se tem um caso ativo.
    caso = Caso.objects.filter(ativo=True).first()
    if not caso:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')
    
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
    ocorrencias = Ocorrencia.objects.filter(caso=caso)
    
    total_movimentacao = sum(parse_valor(com.campo_a) for com in comunicacoes if com.campo_a)
    total_creditos = sum(parse_valor(com.campo_b) for com in comunicacoes if com.campo_b)
    total_debitos = sum(parse_valor(com.campo_c) for com in comunicacoes if com.campo_c)
    
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
    
    return render(request, 'casos/relatorio.html', context)


def relatorio_documento(request):
    """Gera relatório financeiro do caso"""
    
    # Testa se tem um caso ativo.
    caso = Caso.objects.filter(ativo=True).first()
    if not caso:
        messages.error(
            request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
        return redirect('casos')
    
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
        movimentacao_rif = sum(parse_valor(com.campo_a) for com in comunicacoes if com.caso == rif_dict['caso'])
        rifs_list[i]['movimentacao'] = moeda(movimentacao_rif)
    
    # Filtra os titulares e representantes
    titulares = envolvidos.filter(tipo_envolvido='Titular').values('cpf_cnpj_envolvido', 'nome_envolvido', 'tipo_envolvido', 'indexador').distinct().order_by('nome_envolvido')
    representantes = envolvidos.filter(tipo_envolvido='Representante').values('cpf_cnpj_envolvido', 'nome_envolvido', 'tipo_envolvido', 'indexador').distinct().order_by('nome_envolvido')
    
    # Total movimentado no Caso
    movimentacao = sum(parse_valor(com.campo_a) for com in comunicacoes if com.campo_a)
    
    # Total movimentado por titular
    for i, titular in enumerate(titulares):
        movimentacao_titular = sum(parse_valor(com.campo_a) for com in comunicacoes if com.campo_a and com.indexador == titular['cpf_cnpj_envolvido'])
        titulares[i]['movimentacao'] = moeda(movimentacao_titular)
        titulares[i]['creditos'] = moeda(sum(parse_valor(com.campo_b) for com in comunicacoes if com.indexador == titular['indexador']))
        titulares[i]['debitos'] = moeda(sum(parse_valor(com.campo_c) for com in comunicacoes if com.indexador == titular['indexador']))


    df_rifdetalhado = pd.DataFrame()
    
    # Converter QuerySets para DataFrames
    df_comunicacoes = pd.DataFrame(list(comunicacoes.values('rif__numero', 'informacoes_adicionais', 'campo_a', 'campo_b', 'campo_c')))
    df_envolvidos = pd.DataFrame(list(envolvidos.values('rif__numero', 'nome_envolvido', 'tipo_envolvido')))
    df_ocorrencias = pd.DataFrame(list(ocorrencias.values('rif__numero', 'ocorrencia')))
    
    # Renomear colunas para usar 'numero' como chave
    df_comunicacoes = df_comunicacoes.rename(columns={'rif__numero': 'numero'})
    df_envolvidos = df_envolvidos.rename(columns={'rif__numero': 'numero'})
    df_ocorrencias = df_ocorrencias.rename(columns={'rif__numero': 'numero'})
    
    # Juntar Comunicacao, Envolvido e Ocorrencia no df_rifdetalhado
    if not df_comunicacoes.empty:
        df_rifdetalhado = df_rifdetalhado.merge(df_comunicacoes, on='numero', how='left')
    if not df_envolvidos.empty:
        df_rifdetalhado = df_rifdetalhado.merge(df_envolvidos, on='numero', how='left')
    if not df_ocorrencias.empty:
        df_rifdetalhado = df_rifdetalhado.merge(df_ocorrencias, on='numero', how='left')
    
    print("Colunas do df_rifdetalhado:", df_rifdetalhado.columns.tolist())
    print("Colunas do df_comunicacoes:", df_comunicacoes.columns.tolist())
    print(df_rifdetalhado)

    # Monta os dados para cada alvo
    titulares_extratos = []
    for titular in titulares:
        alvo = titular['nome_envolvido']
        
        print('*******************************************************', alvo)
        
        # Filtrar o DataFrame para o titular atual
        df_alvo = df_rifdetalhado[
            (df_rifdetalhado['nome_envolvido'] == alvo) & 
            (df_rifdetalhado['tipo_envolvido'] == 'Titular')
        ].copy()
        
        print(df_alvo)

        if df_alvo.empty:
            continue

        # Resultado financeiro separado por alvo (movimentação total)
        df_alvo.loc[:, 'campo_a'] = pd.to_numeric(df_alvo['campo_a'], errors='coerce')
        movimentacao = df_alvo['campo_a'].sum()
        df_alvo['campo_a'] = df_alvo['campo_a'].apply(moeda)

        df_alvo.loc[:, 'campo_b'] = pd.to_numeric(df_alvo['campo_b'], errors='coerce')
        creditos = df_alvo['campo_b'].sum()
        df_alvo['campo_b'] = df_alvo['campo_b'].apply(moeda)

        df_alvo.loc[:, 'campo_c'] = pd.to_numeric(df_alvo['campo_c'], errors='coerce')
        debitos = df_alvo['campo_c'].sum()
        df_alvo['campo_c'] = df_alvo['campo_c'].apply(moeda)

        # INFORMAÇÕES ADICIONAIS
        infomacoes_adicionais = []
        for informacao in df_alvo['informacoes_adicionais'].dropna():
            infomacoes_adicionais.append(informacao)

        # OBSERVAÇÕES DO ANALISTA COM < IA >
        informacoes_texto = ' '.join(df_alvo['informacoes_adicionais'].dropna())
        #observacoes_analista = executar_prompt([{
        #    "role": "user",
        #    "content": f"Faça uma breve análise, em formato dissertativo, com um ou dois parágrafos, dessas movimentações bancárias. Anote com quem {alvo} transacionou dinheiro: <movimentacoes_bancarias>{informacoes_texto[0:3000]}</movimentacoes_bancarias>"
        #}])
        
        # KYC - Know Your Client
        kyc = '' #executar_prompt([{
        #    "role": "user",
        #    "content": (f"Preciso fazer uma análise do tipo KYC (know your client) a partir das fichas de anotações de **{alvo}**. Identifique dados como CPF, Profissão, Renda, Bancos que mantém relacionamento, Empresas que é sócio ou tem alguma participação, Período em que os dados foram analisados. Foque ESPECIFICAMENTE nas informações de KYC, e ignore o restante das informações: <anotacoes>{informacoes_texto[0:3000]}</anotacoes>. Escreva um texto de um ou dois paragrafos com essas informações.")
        #}])
        
        titulares_extratos.append({
            'nome': alvo,
            'investigado': False,  # Valor padrão
            'cpf': titular['cpf_cnpj_envolvido'],
            'kyc': kyc,
            'movimentacao_total': moeda(movimentacao),
            'creditos': moeda(creditos),
            'debitos': moeda(debitos),
            'comunicacoes': df_alvo.to_dict(orient='records'),
            'comunicacoes_nao_suspeitas': df_alvo[df_alvo['codigo_segmento'] != 41].to_dict(orient='records') if 'codigo_segmento' in df_alvo.columns else [],
            'outras_informacoes': infomacoes_adicionais,
            'observacoes_analista': '', #observacoes_analista,
            'ocorrencias': list(ocorrencias.filter(indexador=titular['indexador']).values('ocorrencia')),
        })
    
    
    
    # Dados que serão impressos no relatório
    data = {
        'rifs': rifs,
        'comunicacoes': comunicacoes,
        'envolvidos': envolvidos,
        'investigados': investigados,
        'titulares': titulares,
        'representantes': representantes,
        'ocorrencias': ocorrencias,
        'movimentacao': moeda(movimentacao),
        'titulares_extratos': titulares_extratos,
    }
    
    try:
        doc = DocxTemplate(f"templates/documentos/rif.docx")
        
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
        
        # Remove o arquivo temporário
        try:
            os.unlink(temp_path)
        except:
            pass
        
        # Envia o arquivo para o cliente
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="Relatorio Inteligência Financeira.zip"'
        return response

    except Exception as e:
        print(e)
        return redirect('/financeira/index/')