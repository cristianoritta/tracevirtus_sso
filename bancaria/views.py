from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from .models import Cooperacao, ExtratoDetalhado
from app.models import Caso, Arquivo
from django.contrib import messages
import pandas as pd
from django.core.files.storage import default_storage
import hashlib
from datetime import datetime
import json
from django.db.models import Sum, Count, F, Case, When, FloatField, Q
from django.db.models.functions import TruncMonth, TruncDay
from django.core.serializers.json import DjangoJSONEncoder
import csv
from docxtpl import DocxTemplate, InlineImage
from io import BytesIO
import os
import tempfile
from num2words import num2words
import matplotlib
matplotlib.use('Agg') # Use a non-interactive backend for environments without a display
import matplotlib.pyplot as plt
from docx.shared import Mm
from utils.ia import executar_prompt
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.db.models.functions import Substr, Length
from django.db.models import Sum, Case, When, F, Value, CharField
from django.db.models.functions import Concat
from django.http import JsonResponse
from datetime import datetime
import json


# Helper function for currency formatting
def moeda(valor):
    if valor is None or not isinstance(valor, (int, float)):
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@login_required
def index(request):
    # Obtém todas as cooperações bancárias
    cooperacoes = Cooperacao.objects.select_related('caso').all().order_by('-created_at')
    
    for i, cooperacao in enumerate(cooperacoes):
        cooperacoes[i].arquivos = Arquivo.objects.filter(external_id=cooperacao.id, tipo='cooperacao_bancaria').count()
        cooperacoes[i].titulares = ExtratoDetalhado.objects.filter(cooperacao=cooperacao).values('cpf_cnpj_titular').distinct().count()
    
    if request.method == 'POST':
        try:
            numero = request.POST.get('numero')
            inquerito = request.POST.get('inquerito')
            processo = request.POST.get('processo')
            
            # Testa se tem um caso ativo.
            caso = Caso.objects.filter(ativo=True).first()
            if not caso:
                messages.error(
                    request, 'Nenhum caso ativo encontrado. Por favor, cadastre um caso para continuar.')
                return redirect('casos')
            
            cooperacao = Cooperacao.objects.create(
                caso=caso,
                numero=numero,
                inquerito=inquerito,
                processo=processo
            )
            
            return redirect('bancaria:index')
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    
    context = {
        'cooperacoes': cooperacoes,
        'total_cooperacoes': cooperacoes.count(),
        'title': 'Gerenciar Cooperações Bancárias',
        'subtitle': 'Gerencie as cooperações bancárias cadastradas no sistema'
    }
    
    return render(request, 'bancaria/index.html', context)

@login_required
@require_http_methods(["DELETE"])
def delete_cooperacao(request, id):
    cooperacao = get_object_or_404(Cooperacao, id=id)
    cooperacao.delete()
    return JsonResponse({'message': 'Cooperação excluída com sucesso'})

@login_required
@require_http_methods(["POST"])
def importar_arquivos(request):
    try:
        if 'arquivo' not in request.FILES:
            return JsonResponse({'error': 'Nenhum arquivo recebido'}, status=400)

        arquivo = request.FILES['arquivo']
        
        # Verifica se é um arquivo de extrato detalhado
        if not arquivo.name.lower().find('extratodetalhado') > -1:
            return JsonResponse({'error': 'Arquivo não é um extrato detalhado'}, status=400)

        # Obtém o caso ativo
        caso = Caso.objects.filter(ativo=True).first()
        if not caso:
            return JsonResponse({'error': 'Nenhum caso ativo encontrado'}, status=400)

        # Obtém a cooperação ativa
        cooperacao = Cooperacao.objects.filter(caso=caso).first()
        if not cooperacao:
            return JsonResponse({'error': 'Nenhuma cooperação encontrada para o caso ativo'}, status=400)

        # Salva o arquivo
        file_hash = hashlib.sha256(arquivo.read()).hexdigest()
        arquivo.seek(0)  # Reset file pointer after reading for hash

        # Verifica se o arquivo já foi processado
        if Arquivo.objects.filter(hash=file_hash, caso=caso).exists():
            return JsonResponse({'error': 'Este arquivo já foi processado anteriormente'}, status=400)

        # Processa o arquivo com pandas
        if arquivo.name.endswith('.csv'):
            df = pd.read_csv(arquivo, sep=';')
        elif arquivo.name.endswith('.xlsx'):
            df = pd.read_excel(arquivo)
        else:
            return JsonResponse({'error': 'Formato de arquivo não suportado'}, status=400)

        print("[DEBUG] Arquivo lido com sucesso")

        # Conta o número de registros antes de qualquer processamento
        total_registros = len(df)
        print("[DEBUG] Total de registros:", total_registros)

        # Salva o arquivo no sistema
        arquivo_salvo = Arquivo.objects.create(
            caso=caso,
            nome=arquivo.name,
            hash=file_hash,
            tipo='cooperacao_bancaria',
            external_id=cooperacao.id,
            registros=total_registros
        )
        print("[DEBUG] Arquivo salvo com sucesso")

        # Remove colunas desnecessárias se existirem
        colunas_remover = ['NUMERO_CASO', 'NOME_BANCO']
        for coluna in colunas_remover:
            if coluna in df.columns:
                df = df.drop(coluna, axis=1)
        print("[DEBUG] Colunas removidas")
        
        
        # Converte nomes das colunas para minúsculo
        df.columns = df.columns.str.lower()

        # Renomeia algumas colunas para match com o modelo
        mapeamento_colunas = {
            'numero_banco': 'banco',
            'numero_agencia': 'numero_agencia',
            'numero_conta': 'numero_conta',
            'tipo_conta': 'tipo',
            'nome_titular': 'nome_titular',
            'cpf_cnpj_titular': 'cpf_cnpj_titular',
            'descricao_lancamento': 'descricao_lancamento',
            'data_lancamento': 'data_lancamento',
            'numero_documento': 'numero_documento',
            'numero_documento_transacao': 'numero_documento_transacao',
            'local_transacao': 'local_transacao',
            'valor_transacao': 'valor_transacao',
            'natureza_lancamento': 'natureza_lancamento',
            'valor_saldo': 'valor_saldo',
            'natureza_saldo': 'natureza_saldo',
            'cpf_cnpj_od': 'cpf_cnpj_od',
            'nome_pessoa_od': 'nome_pessoa_od',
            'tipo_pessoa_od': 'tipo_pessoa_od',
            'numero_banco_od': 'numero_banco_od',
            'numero_agencia_od': 'numero_agencia_od',
            'numero_conta_od': 'numero_conta_od'
        }
        df = df.rename(columns=mapeamento_colunas)
        print("[DEBUG] Colunas renomeadas")

        # Converte tipos de dados
        df['data_lancamento'] = pd.to_datetime(df['data_lancamento'], format='%d/%m/%Y', errors='coerce')
        df['valor_transacao'] = df['valor_transacao'].str.replace(',', '.').astype(float)
        df['valor_saldo'] = df['valor_saldo'].str.replace(',', '.').astype(float)
        print("[DEBUG] Tipos de dados convertidos")

        # Trata campos numéricos, convertendo NaN para string vazia
        campos_numericos = ['banco', 'numero_agencia', 'numero_conta', 'tipo', 
                          'numero_banco_od', 'numero_agencia_od', 'numero_conta_od']
        
        try:
            print("[DEBUG] Convertendo tipos de dados")
            for campo in campos_numericos:
                print("[DEBUG] Convertendo campo:", campo)
                # Converte NaN para string vazia
                df[campo] = df[campo].fillna('')
                # Se o campo não estiver vazio, converte para string removendo '.0' do final
                df[campo] = df[campo].apply(lambda x: str(int(float(x))) if str(x).strip() != '' else '')
        except Exception as e:
            print("[DEBUG] Erro ao converter tipos de dados:", e)
        print("[DEBUG] Campos numéricos tratados")

        # Trata campos de texto, convertendo NaN para string vazia
        campos_texto = ['nome_titular', 'cpf_cnpj_titular', 'descricao_lancamento', 'cnab',
                       'numero_documento', 'numero_documento_transacao', 'local_transacao',
                       'natureza_lancamento', 'natureza_saldo', 'cpf_cnpj_od', 'nome_pessoa_od',
                       'tipo_pessoa_od', 'observacao', 'nome_endossante_cheque', 'doc_endossante_cheque']
        
        for campo in campos_texto:
            if campo in df.columns:
                df[campo] = df[campo].fillna('').astype(str)
        print("[DEBUG] Campos tratados")

        # Cria os registros no banco de dados
        registros = []
        for _, row in df.iterrows():
            registro = ExtratoDetalhado(
                cooperacao=cooperacao,
                caso=caso,
                arquivo=arquivo_salvo,
                banco=row['banco'],
                numero_agencia=row['numero_agencia'],
                numero_conta=row['numero_conta'],
                tipo=row['tipo'],
                nome_titular=row['nome_titular'],
                cpf_cnpj_titular=row['cpf_cnpj_titular'],
                descricao_lancamento=row['descricao_lancamento'],
                cnab=row.get('cnab', ''),
                data_lancamento=row['data_lancamento'],
                numero_documento=row['numero_documento'],
                numero_documento_transacao=row['numero_documento_transacao'],
                local_transacao=row['local_transacao'],
                valor_transacao=row['valor_transacao'],
                natureza_lancamento=row['natureza_lancamento'],
                valor_saldo=row['valor_saldo'],
                natureza_saldo=row['natureza_saldo'],
                cpf_cnpj_od=row['cpf_cnpj_od'],
                nome_pessoa_od=row['nome_pessoa_od'],
                tipo_pessoa_od=row['tipo_pessoa_od'],
                numero_banco_od=row['numero_banco_od'],
                numero_agencia_od=row['numero_agencia_od'],
                numero_conta_od=row['numero_conta_od'],
                observacao=row.get('observacao', ''),
                nome_endossante_cheque=row.get('nome_endossante_cheque', ''),
                doc_endossante_cheque=row.get('doc_endossante_cheque', '')
            )
            registros.append(registro)

        print("VEIO ATE AKI")

        # Salva todos os registros de uma vez
        ExtratoDetalhado.objects.bulk_create(registros)

        return redirect('bancaria:index')
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def gerar_relatorio_bancario(request):
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos:index')

    doc = DocxTemplate(f"templates/documentos/simba.docx")

    # Coleta todos os extratos e carrega em um DataFrame do Pandas
    extratos_qs = ExtratoDetalhado.objects.filter(caso=caso_ativo).values()
    if not extratos_qs.exists():
        messages.error(request, 'Não há dados bancários para gerar o relatório neste caso.')
        return redirect('bancaria:dashboard')
        
    df_extratodetalhado = pd.DataFrame(list(extratos_qs))
    df_extratodetalhado['valor_transacao'] = pd.to_numeric(df_extratodetalhado['valor_transacao'], errors='coerce').fillna(0)
    df_extratodetalhado['data_lancamento'] = pd.to_datetime(df_extratodetalhado['data_lancamento'], errors='coerce')

    # --- INÍCIO DA LÓGICA DE ANÁLISE ---

    cooperacoes = Cooperacao.objects.filter(caso=caso_ativo)
    arquivos = Arquivo.objects.filter(caso=caso_ativo, tipo='cooperacao_bancaria').values('nome', 'hash').distinct()

    metodologia = 'Carta Circular'
    for arquivo in arquivos:
        if 'extrato' in arquivo['nome'].lower():
            metodologia = 'Extrato Detalhado'
            break
            
    contas = df_extratodetalhado.groupby(['nome_titular', 'banco', 'numero_agencia', 'numero_conta']).first().reset_index()
    titulares = df_extratodetalhado.groupby(['nome_titular', 'cpf_cnpj_titular']).first().reset_index()
    bancos = df_extratodetalhado.groupby(['banco']).first().reset_index()

    total_movimentacoes_val = df_extratodetalhado['valor_transacao'].sum()
    total_movimentacoes = {
        'total': moeda(total_movimentacoes_val),
        'extenso': num2words(total_movimentacoes_val, lang='pt_BR', to="currency")
    }

    total_movimentacoes_investigado = df_extratodetalhado.groupby('nome_titular')['valor_transacao'].sum().reset_index()
    total_movimentacoes_investigado['total'] = total_movimentacoes_investigado['valor_transacao'].apply(moeda)

    # Créditos e Débitos acima de um limite
    valor_corte = 5000
    creditos_acima = (
        df_extratodetalhado[
            (df_extratodetalhado['natureza_lancamento'] == 'C') &
            (df_extratodetalhado['cpf_cnpj_titular'] != df_extratodetalhado['cpf_cnpj_od'])
        ]
        .groupby(['cpf_cnpj_od', 'nome_pessoa_od', 'nome_titular'])
        .agg(valor=('valor_transacao', 'sum'), quantidade=('valor_transacao', 'count'))
        .sort_values(by='valor', ascending=True)
        .reset_index()
    )
    creditos_acima = creditos_acima[creditos_acima['valor'] > valor_corte]
    creditos_acima['valor_formatado'] = creditos_acima['valor'].apply(moeda)
    
    debitos_acima = (
        df_extratodetalhado[
            (df_extratodetalhado['natureza_lancamento'] == 'D') &
            (df_extratodetalhado['cpf_cnpj_titular'] != df_extratodetalhado['cpf_cnpj_od'])
        ]
        .groupby(['cpf_cnpj_od', 'nome_pessoa_od', 'nome_titular'])
        .agg(valor=('valor_transacao', 'sum'), quantidade=('valor_transacao', 'count'))
        .sort_values(by=['nome_titular', 'valor'], ascending=[True, True])
        .reset_index()
    )
    debitos_acima = debitos_acima[debitos_acima['valor'] > valor_corte]
    debitos_acima['valor_formatado'] = debitos_acima['valor'].apply(moeda)

    # Identificar contrapartes com múltiplos titulares
    multiplos_titulares = df_extratodetalhado.groupby('nome_pessoa_od')['nome_titular'].nunique().reset_index(name='quantidade')
    multiplos_titulares = multiplos_titulares[multiplos_titulares['quantidade'] > 1]
    resultados = df_extratodetalhado[
        df_extratodetalhado['nome_pessoa_od'].isin(multiplos_titulares['nome_pessoa_od'])
    ][['cpf_cnpj_od', 'nome_pessoa_od', 'nome_titular']].drop_duplicates()
    contrapartes_multiplos_titulares = multiplos_titulares.merge(resultados, on='nome_pessoa_od')

    # --- Análise de Alvos ---
    alvos_extratos = []
    temp_files = [] # Armazena os paths dos gráficos temporários para exclusão posterior
    
    for _, titular_row in titulares.iterrows():
        alvo = titular_row['nome_titular']
        df_alvo = df_extratodetalhado[df_extratodetalhado['nome_titular'] == alvo].copy()

        movimentacao = df_alvo['valor_transacao'].sum()
        creditos = df_alvo[df_alvo['natureza_lancamento'] == 'C']['valor_transacao'].sum()
        debitos = df_alvo[df_alvo['natureza_lancamento'] == 'D']['valor_transacao'].sum()

        # Créditos e débitos em dinheiro
        creditos_dinheiro = df_alvo[(df_alvo['natureza_lancamento'] == 'C') & (df_alvo['descricao_lancamento'].str.contains('DP DIN|DINHEIRO', case=False, regex=True, na=False))]['valor_transacao'].sum()
        debitos_dinheiro = df_alvo[(df_alvo['natureza_lancamento'] == 'D') & (df_alvo['descricao_lancamento'].str.contains('saque', case=False, na=False))]['valor_transacao'].sum()

        # Salário
        salario = df_alvo[(df_alvo['natureza_lancamento'] == 'C') & (df_alvo['descricao_lancamento'].str.contains('folha.*pagamento|salari', regex=True, case=False, na=False))]['valor_transacao'].sum()

        # Evolução Mensal (Gráfico)
        df_alvo['mesano'] = pd.to_datetime(df_alvo['data_lancamento']).dt.to_period("M")
        evolucao_mensal = df_alvo.groupby('mesano')['valor_transacao'].sum().reset_index()
        evolucao_mensal['mesano'] = evolucao_mensal['mesano'].dt.strftime('%b/%Y').str.lower()
        meses_pt = {'jan': 'jan', 'feb': 'fev', 'mar': 'mar', 'apr': 'abr', 'may': 'mai', 'jun': 'jun', 'jul': 'jul', 'aug': 'ago', 'sep': 'set', 'oct': 'out', 'nov': 'nov', 'dec': 'dez'}
        evolucao_mensal['mesano'] = evolucao_mensal['mesano'].replace(meses_pt, regex=True)

        plt.figure(figsize=(8, 5))
        plt.bar(evolucao_mensal['mesano'], evolucao_mensal['valor_transacao'], color='blue')
        plt.title("Evolução Mensal")
        plt.xlabel("Mês/Ano")
        plt.ylabel("Valor (R$)")
        plt.xticks(rotation=45, fontsize=10)
        plt.tight_layout()
        
        chart_path = os.path.join(tempfile.gettempdir(), f"evolucao_{alvo}.png")
        plt.savefig(chart_path)
        plt.close()
        temp_files.append(chart_path)
        evolucao_mensal_grafico = InlineImage(doc, chart_path, width=Mm(160))
        
        evolucao_mensal_tabela = evolucao_mensal.copy()
        evolucao_mensal_tabela['valor_transacao'] = evolucao_mensal_tabela['valor_transacao'].apply(moeda)

        # 10 Maiores créditos por contraparte
        maiores_creditos_contraparte = df_alvo[
            (df_alvo['natureza_lancamento'] == 'C') & (df_alvo['cpf_cnpj_od'].notna())
        ].groupby(['cpf_cnpj_od', 'nome_pessoa_od']).agg(
            valor=('valor_transacao', 'sum'), quantidade=('valor_transacao', 'count')
        ).nlargest(10, 'valor').reset_index()
        maiores_creditos_contraparte['valor'] = maiores_creditos_contraparte['valor'].apply(moeda)

        # 10 Maiores débitos por contraparte
        maiores_debitos_contraparte = df_alvo[
            (df_alvo['natureza_lancamento'] == 'D') & (df_alvo['cpf_cnpj_od'].notna())
        ].groupby(['cpf_cnpj_od', 'nome_pessoa_od']).agg(
            valor=('valor_transacao', 'sum'), quantidade=('valor_transacao', 'count')
        ).nlargest(10, 'valor').reset_index()
        maiores_debitos_contraparte['valor'] = maiores_debitos_contraparte['valor'].apply(moeda)

        # Tipologia: Smurfing
        smurfing_limite = 100
        df_filtrado_smurf = df_alvo[(df_alvo['valor_transacao'] > smurfing_limite) & (df_alvo['natureza_lancamento'] == 'C')]
        smurfing = df_filtrado_smurf.groupby(['data_lancamento', 'valor_transacao', 'nome_pessoa_od']) \
            .agg(quantidade=('valor_transacao', 'count'), soma_valor=('valor_transacao', 'sum')).reset_index()
        smurfing = smurfing[smurfing['quantidade'] > 1]
        if not smurfing.empty:
            smurfing['data_lancamento'] = pd.to_datetime(smurfing['data_lancamento']).dt.strftime('%d/%m/%Y')
            smurfing['valor'] = smurfing['valor_transacao'].apply(moeda)
            smurfing['soma_valor'] = smurfing['soma_valor'].apply(moeda)

        # Tipologia: Saldo Zero
        saldo_diario = df_alvo.groupby('data_lancamento').apply(
            lambda x: x.loc[x['natureza_lancamento'] == 'C', 'valor_transacao'].sum() - x.loc[x['natureza_lancamento'] == 'D', 'valor_transacao'].sum()
        ).reset_index(name='saldo')
        saldo_zero = saldo_diario[saldo_diario['saldo'] == 0].reset_index(drop=True)
        if not saldo_zero.empty:
            saldo_zero['saldo'] = saldo_zero['saldo'].apply(moeda)
            saldo_zero['data_lancamento'] = pd.to_datetime(saldo_zero['data_lancamento']).dt.strftime('%d/%m/%Y')

        # Tipologia: Créditos Cruzados
        df_creditos = df_alvo[df_alvo['natureza_lancamento'] == 'C'].groupby(['cpf_cnpj_od', 'nome_pessoa_od'])['valor_transacao'].sum().reset_index()
        df_creditos = df_creditos.rename(columns={'valor_transacao': 'soma_creditos'})
        df_debitos = df_alvo[df_alvo['natureza_lancamento'] == 'D'].groupby(['cpf_cnpj_od', 'nome_pessoa_od'])['valor_transacao'].sum().reset_index()
        df_debitos = df_debitos.rename(columns={'valor_transacao': 'soma_debitos'})
        df_creditoscruzados = pd.merge(df_creditos, df_debitos, on=['cpf_cnpj_od', 'nome_pessoa_od'], how='outer').fillna(0)
        df_creditoscruzados = df_creditoscruzados[(df_creditoscruzados['soma_creditos'] != 0) & (df_creditoscruzados['soma_debitos'] != 0)]
        if not df_creditoscruzados.empty:
            df_creditoscruzados['soma_creditos'] = df_creditoscruzados['soma_creditos'].apply(moeda)
            df_creditoscruzados['soma_debitos'] = df_creditoscruzados['soma_debitos'].apply(moeda)

        # Transações entre alvos
        nomes_alvos = titulares['nome_titular'].tolist()
        entrealvos = df_extratodetalhado[
            (df_extratodetalhado['nome_pessoa_od'] == alvo) & 
            (df_extratodetalhado['nome_titular'].isin(nomes_alvos)) &
            (df_extratodetalhado['nome_titular'] != alvo)
        ].groupby('nome_titular')['valor_transacao'].sum().nlargest(10).reset_index()
        entrealvos['valor'] = entrealvos['valor_transacao'].apply(moeda)
        
        # Transações entre contas do próprio alvo (Zé com Zé)
        entrecontas = df_alvo[df_alvo['nome_titular'] == df_alvo['nome_pessoa_od']]
        total_entrecontas = entrecontas['valor_transacao'].sum()
        quantidade_entrecontas = len(entrecontas)

        # Tipologia: Múltiplos Saques no mesmo dia
        df_saques_dia = df_alvo[
            (df_alvo['natureza_lancamento'] == 'D') & 
            (df_alvo['descricao_lancamento'].str.contains('SAQUE', case=False, na=False))
        ]
        contagem_saques = df_saques_dia.groupby('data_lancamento').size().reset_index(name='quantidade_saques')
        datas_multiplos_saques = contagem_saques[contagem_saques['quantidade_saques'] > 1]['data_lancamento']
        df_saques = pd.DataFrame()
        if not datas_multiplos_saques.empty:
            df_saques = df_saques_dia[df_saques_dia['data_lancamento'].isin(datas_multiplos_saques)]
            df_saques = df_saques.groupby('data_lancamento').agg(soma_debitos=('valor_transacao', 'sum')).reset_index()
            df_saques = df_saques.merge(contagem_saques, on='data_lancamento')
            df_saques['data_lancamento'] = pd.to_datetime(df_saques['data_lancamento']).dt.strftime('%d/%m/%Y')
            df_saques['soma_debitos'] = df_saques['soma_debitos'].apply(moeda)

        
        # Criar um dataframe com as movimentações do alvo consolidadas por contraparte e natureza
        df_alvo_filtrado_od = df_alvo.dropna(subset=['cpf_cnpj_od'])
        df_alvo_filtrado_od = df_alvo_filtrado_od[df_alvo_filtrado_od['cpf_cnpj_od'] != '']

        df_alvo_consolidado = df_alvo_filtrado_od.groupby(
            ['nome_pessoa_od', 'cpf_cnpj_od', 'natureza_lancamento']
        ).agg(
            valor_transacao=('valor_transacao', 'sum'),
            quantidade=('valor_transacao', 'count')
        ).reset_index()
        df_alvo_consolidado = df_alvo_consolidado.sort_values(by='valor_transacao', ascending=False)
        
        # ANALISE COM IA
        analise_ia = ""
        try:
            if not df_alvo_consolidado.empty:
                prompt_content = f"""Você é um especialista em investigação financeira e lavagem de dinheiro. Elabore um relatório em formato de texto corrido, com 3 ou quatro parágrafos, analisando as principais movimentações financeiras do titular {alvo}, com base nos seguintes dados consolidados. Faça um paragrafo geral, sobre a estrutura das movimentações financeiras, o segundo, sobre os créditos (C), o terceiro sobre os débitos (D) e o ultimo como uma conclusão indicando sobre a possível lavagem de dinheiro, especialmente em razão das outras provas coletadaas na investigação.
                ATENÇÃO. Sua resposta deve ser um texto corrido, com 3 ou quatro parágrafos, sem nenhum outro comentário, apresentação etc. Não use markdown.
<extrato>
{df_alvo_consolidado.to_string()}
</extrato>
"""
                analise_ia = executar_prompt([
                    {"role": "user", "content": prompt_content}
                ])
        except Exception as e:
            print(f"Erro ao executar a análise de IA para {alvo}: {e}")
            analise_ia = "Não foi possível gerar a análise por IA."
            
        alvos_extratos.append({
            'nome_investigado': alvo,
            'movimentacao_total': moeda(movimentacao),
            'movimentacao_total_extenso': num2words(movimentacao, lang='pt_BR', to="currency"),
            'creditos': moeda(creditos),
            'debitos': moeda(debitos),
            'creditos_dinheiro': moeda(creditos_dinheiro),
            'debitos_dinheiro': moeda(debitos_dinheiro),
            'salario': salario,
            'salario_total': moeda(salario),
            'salario_extenso': num2words(salario, lang='pt_BR', to="currency"),
            'evolucao_mensal': evolucao_mensal_tabela.to_dict(orient='records'),
            'evolucao_mensal_grafico': evolucao_mensal_grafico,
            'creditos_maiores_contraparte': maiores_creditos_contraparte.to_dict(orient='records'),
            'debitos_maiores_contraparte': maiores_debitos_contraparte.to_dict(orient='records'),
            'smurfing': smurfing.to_dict(orient='records'),
            'saldo_zero': saldo_zero.to_dict(orient='records'),
            'creditos_cruzados': df_creditoscruzados.to_dict(orient='records'),
            'saques': df_saques.to_dict(orient='records'),
            'entrealvos': entrealvos.to_dict(orient='records'),
            'entrealvos_quantidade': len(entrealvos),
            'movimentacao_entrecontas': moeda(total_entrecontas),
            'movimentacao_entrecontas_quantidade': quantidade_entrecontas,
            'analise_ia': analise_ia,
            'antecedentes': [], # Placeholder para futuros dados de antecedentes
        })

    # Placeholder para antecedentes de contrapartes
    contrapartes_antecedentes = []

    # --- FIM DA ANÁLISE ---

    context = {
        'cooperacoes': cooperacoes,
        'arquivos': list(arquivos),
        'metodologia': metodologia,
        'bancos': bancos.to_dict(orient='records'),
        'contas': contas.to_dict(orient='records'),
        'titulares': titulares.to_dict(orient='records'),
        'total_movimentacoes': total_movimentacoes,
        'total_movimentacoes_investigado': total_movimentacoes_investigado.to_dict(orient='records'),
        'creditos_acima': creditos_acima.to_dict(orient='records'),
        'debitos_acima': debitos_acima.to_dict(orient='records'),
        'contrapartes_multiplos_titulares': contrapartes_multiplos_titulares.to_dict(orient='records'),
        'contrapartes_antecedentes': contrapartes_antecedentes,
        'alvos_extratos': alvos_extratos,
        'caso_numero': caso_ativo.numero,
        'inquerito': cooperacoes.first().inquerito if cooperacoes.exists() else 'N/A',
        'processo': cooperacoes.first().processo if cooperacoes.exists() else 'N/A',
    }

    doc.render(context)
    
    for path in temp_files:
        try:
            os.remove(path)
        except OSError:
            pass # Ignore if file not found

    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)

    response = HttpResponse(bio.getvalue(), content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    response['Content-Disposition'] = f'attachment; filename="relatorio_tecnico_{caso_ativo.numero}.docx"'
    return response


@login_required
def listar_arquivos(request, cooperacao_id):
    # Obtém a cooperação
    cooperacao = get_object_or_404(Cooperacao, id=cooperacao_id)
    
    # Verifica se a cooperação pertence ao caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo or cooperacao.caso != caso_ativo:
        messages.error(request, 'Esta cooperação não pertence ao caso ativo.')
        return redirect('bancaria:index')
    
    # Obtém os arquivos
    arquivos = Arquivo.objects.filter(
        external_id=cooperacao_id,
        tipo='cooperacao_bancaria'
    ).order_by('-created_at')
    
    # Obtém os extratos detalhados para cada arquivo
    for arquivo in arquivos:
        arquivo.total_registros = ExtratoDetalhado.objects.filter(
            arquivo=arquivo,
            cooperacao=cooperacao
        ).count()
    
    context = {
        'cooperacao': cooperacao,
        'arquivos': arquivos,
        'title': f'Arquivos da Cooperação {cooperacao.numero}',
        'subtitle': f'Inquérito: {cooperacao.inquerito} - Processo: {cooperacao.processo}'
    }
    
    return render(request, 'bancaria/arquivos.html', context)

@login_required
@require_http_methods(["DELETE"])
def delete_arquivo(request, id):
    arquivo = get_object_or_404(Arquivo, id=id)
    
    # Verifica se o arquivo pertence ao caso ativo
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo or arquivo.caso != caso_ativo:
        return JsonResponse({'error': 'Este arquivo não pertence ao caso ativo'}, status=403)
    
    # Exclui os registros de extrato detalhado associados
    ExtratoDetalhado.objects.filter(arquivo=arquivo).delete()
    
    # Exclui o arquivo
    arquivo.delete()
    
    return JsonResponse({'message': 'Arquivo excluído com sucesso'})

@login_required
def dashboard(request):
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos:index')

    extratos = ExtratoDetalhado.objects.filter(caso=caso_ativo)

    if not extratos.exists():
        context = {
            'title': 'Dashboard de Análise Bancária',
            'subtitle': f'Caso: {caso_ativo.numero}',
            'no_data': True
        }
        return render(request, 'bancaria/dashboard.html', context)

    # 1. Métricas Principais (Cards)
    total_credito = extratos.filter(natureza_lancamento='C').aggregate(Sum('valor_transacao'))['valor_transacao__sum'] or 0
    total_debito = extratos.filter(natureza_lancamento='D').aggregate(Sum('valor_transacao'))['valor_transacao__sum'] or 0
    total_transacoes = extratos.count()
    contas_unicas = extratos.values('cpf_cnpj_titular').distinct().count()

    # 2. Gráfico de Movimentação no Tempo (Crédito vs. Débito)
    movimentacao_tempo = extratos.annotate(
        mes=TruncMonth('data_lancamento')
    ).values('mes').annotate(
        credito=Sum(Case(When(natureza_lancamento='C', then=F('valor_transacao')), default=0, output_field=FloatField())),
        debito=Sum(Case(When(natureza_lancamento='D', then=F('valor_transacao')), default=0, output_field=FloatField()))
    ).order_by('mes')

    # 3. Gráfico de Maiores Titulares
    maiores_titulares_credito = extratos.filter(natureza_lancamento='C').values(
        'nome_titular'
    ).annotate(total=Sum('valor_transacao')).order_by('-total')[:10]
    
    maiores_titulares_debito = extratos.filter(natureza_lancamento='D').values(
        'nome_titular'
    ).annotate(total=Sum('valor_transacao')).order_by('-total')[:10]

    # 4. Gráfico de Pizza (Natureza da Transação)
    distribuicao_natureza = {
        'credito': total_credito,
        'debito': total_debito
    }

    # 5. Maiores Transações (Tabela)
    maiores_transacoes = extratos.order_by('-valor_transacao')[:10]

    # 6. Maiores Destinatários/Origens
    maiores_od = extratos.exclude(
        nome_pessoa_od__isnull=True
    ).exclude(
        nome_pessoa_od=''
    ).values(
        'nome_pessoa_od'
    ).annotate(
        total=Sum('valor_transacao'),
        count=Count('id')
    ).order_by('-total')[:10]

    context = {
        'title': 'Dashboard de Análise Bancária',
        'subtitle': f'Caso: {caso_ativo.numero}',
        'no_data': False,
        
        # Cards
        'total_movimentado': total_credito + total_debito,
        'total_credito': total_credito,
        'total_debito': total_debito,
        'total_transacoes': total_transacoes,
        'contas_unicas': contas_unicas,
        
        # Tabela
        'maiores_transacoes': maiores_transacoes,

        # Dados para Gráficos (em JSON)
        'movimentacao_tempo_json': json.dumps(list(movimentacao_tempo), cls=DjangoJSONEncoder),
        'maiores_titulares_credito_json': json.dumps(list(maiores_titulares_credito), cls=DjangoJSONEncoder),
        'maiores_titulares_debito_json': json.dumps(list(maiores_titulares_debito), cls=DjangoJSONEncoder),
        'distribuicao_natureza_json': json.dumps(distribuicao_natureza, cls=DjangoJSONEncoder),
        'maiores_od_json': json.dumps(list(maiores_od), cls=DjangoJSONEncoder),
    }

    return render(request, 'bancaria/dashboard.html', context)


@login_required
def extrato_detalhado(request):
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos:index')

    cooperacoes = Cooperacao.objects.filter(caso=caso_ativo).order_by('numero')
    
    selected_cooperacao_id = request.GET.get('cooperacao_id')

    extratos = ExtratoDetalhado.objects.filter(caso=caso_ativo).select_related('cooperacao', 'arquivo')

    if selected_cooperacao_id and selected_cooperacao_id != 'all':
        extratos = extratos.filter(cooperacao_id=selected_cooperacao_id)
    
    context = {
        'title': 'Extrato Detalhado',
        'subtitle': f'Caso: {caso_ativo.numero}',
        'extratos': extratos,
        'cooperacoes': cooperacoes,
        'selected_cooperacao_id': selected_cooperacao_id or 'all'
    }

    return render(request, 'bancaria/extrato_detalhado.html', context)


@login_required
def unificar_dados(request):
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos:index')

    if request.method == 'POST':
        cpf_cnpj = request.POST.get('cpf_cnpj')
        nome_manter = request.POST.get('nome_manter')
        nomes_agrupar = request.POST.getlist('nome_agrupar')

        if not all([cpf_cnpj, nome_manter, nomes_agrupar]):
            messages.error(request, 'Informações insuficientes para realizar a unificação.')
            return redirect('bancaria:unificar_dados')

        # Unificar nome_titular
        ExtratoDetalhado.objects.filter(
            caso=caso_ativo,
            cpf_cnpj_titular=cpf_cnpj,
            nome_titular__in=nomes_agrupar
        ).update(
            nome_titular=nome_manter
        )

        # Unificar nome_pessoa_od (origem/destino)
        ExtratoDetalhado.objects.filter(
            caso=caso_ativo,
            cpf_cnpj_od=cpf_cnpj,
            nome_pessoa_od__in=nomes_agrupar
        ).update(
            nome_pessoa_od=nome_manter
        )
        
        messages.success(request, f'Nomes para o CPF/CNPJ {cpf_cnpj} foram unificados para "{nome_manter}".')
        return redirect('bancaria:unificar_dados')

    # GET request
    titulares = ExtratoDetalhado.objects.filter(
        caso=caso_ativo
    ).exclude(
        cpf_cnpj_titular__isnull=True
    ).exclude(
        cpf_cnpj_titular=''
    ).values(
        'cpf_cnpj_titular', 'nome_titular'
    ).distinct().order_by('cpf_cnpj_titular', 'nome_titular')

    # UNIFICAR OS CPFs de _OD
    pessoas_od = ExtratoDetalhado.objects.filter(
        caso=caso_ativo
    ).exclude(
        cpf_cnpj_od__isnull=True
    ).exclude(
        cpf_cnpj_od=''
    ).values(
        'cpf_cnpj_od'
    ).distinct().order_by('cpf_cnpj_od')

    # Atualiza CPFs que terminam em .0
    ExtratoDetalhado.objects.filter(
        caso=caso_ativo,
        cpf_cnpj_titular__endswith='.0'
    ).update(
        cpf_cnpj_titular=Substr('cpf_cnpj_titular', 1, Length('cpf_cnpj_titular') - 2)
    )

    ExtratoDetalhado.objects.filter(
        caso=caso_ativo,
        cpf_cnpj_od__endswith='.0'
    ).update(
        cpf_cnpj_od=Substr('cpf_cnpj_od', 1, Length('cpf_cnpj_od') - 2)
    )

    context = {
        'title': 'Unificar Dados de Titulares',
        'subtitle': f'Caso: {caso_ativo.numero}',
        'titulares': titulares,
        'pessoas_od': pessoas_od,
    }

    return render(request, 'bancaria/unificar_dados.html', context)


@login_required
def listar_titulares(request, cooperacao_id):
    cooperacao = get_object_or_404(Cooperacao, id=cooperacao_id)
    caso_ativo = cooperacao.caso

    # Agrega os dados por titular
    titulares = ExtratoDetalhado.objects.filter(
        cooperacao=cooperacao
    ).values(
        'cpf_cnpj_titular', 'nome_titular'
    ).annotate(
        total_movimentado=Sum('valor_transacao'),
        total_credito=Sum(Case(When(natureza_lancamento='C', then=F('valor_transacao')), default=0, output_field=FloatField())),
        total_debito=Sum(Case(When(natureza_lancamento='D', then=F('valor_transacao')), default=0, output_field=FloatField())),
        total_operacoes=Count('id')
    ).order_by('-total_movimentado')

    context = {
        'title': f'Titulares da Cooperação {cooperacao.numero}',
        'subtitle': f'Caso: {caso_ativo.numero}',
        'cooperacao': cooperacao,
        'titulares': titulares
    }
    
    return render(request, 'bancaria/titulares.html', context)


@login_required
def analise_de_vinculos(request):
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos:index')

    transacoes = ExtratoDetalhado.objects.filter(
        caso=caso_ativo
    ).exclude(
        cpf_cnpj_od__isnull=True
    ).exclude(
        cpf_cnpj_od=''
    ).exclude(
        cpf_cnpj_titular=F('cpf_cnpj_od')
    )

    titulares_cooperacao = list(ExtratoDetalhado.objects.filter(cooperacao__caso=caso_ativo).values_list('cpf_cnpj_titular', flat=True).distinct())

    # Coleta todos os nós (participantes)
    nodes_dict = {}
    for t in transacoes.values('cpf_cnpj_titular', 'nome_titular').distinct():
        cpf = t['cpf_cnpj_titular']
        if cpf and cpf not in nodes_dict:
            nodes_dict[cpf] = {'id': cpf, 'nome': t['nome_titular'], 'cpf_cnpj': cpf, 'tipo': 'Titular'}

    for t in transacoes.values('cpf_cnpj_od', 'nome_pessoa_od').distinct():
        cpf = t['cpf_cnpj_od']
        if cpf and cpf not in nodes_dict:
            nodes_dict[cpf] = {'id': cpf, 'nome': t['nome_pessoa_od'], 'cpf_cnpj': cpf, 'tipo': 'Outro'}

    nodes = list(nodes_dict.values())
    
    # Agrupa as transações para formar os links, separando por natureza
    links_query = transacoes.values('cpf_cnpj_titular', 'cpf_cnpj_od', 'natureza_lancamento').annotate(
        value=Sum('valor_transacao')
    ).order_by('-value')

    links = [
        {
            'source': l['cpf_cnpj_titular'],
            'target': l['cpf_cnpj_od'],
            'value': l['value'],
            'natureza': l['natureza_lancamento']
        }
        for l in links_query if l['cpf_cnpj_titular'] in nodes_dict and l['cpf_cnpj_od'] in nodes_dict
    ]

    context = {
        'title': 'Análise de Vínculos',
        'subtitle': f'Caso: {caso_ativo.numero}',
        'nodes': json.dumps(nodes),
        'links': json.dumps(links, cls=DjangoJSONEncoder),
        'caso': caso_ativo
    }

    return render(request, 'bancaria/analisedevinculos.html', context)


@login_required
def download_vinculos_csv(request):
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        return HttpResponse("Nenhum caso ativo encontrado.", status=404)

    transacoes = ExtratoDetalhado.objects.filter(
        caso=caso_ativo
    ).exclude(
        cpf_cnpj_od__isnull=True
    ).exclude(
        cpf_cnpj_od=''
    ).exclude(
        cpf_cnpj_titular=F('cpf_cnpj_od')
    )

    # Coleta todos os nós para mapear CPF/CNPJ para nome
    nodes_dict = {}
    for t in transacoes.values('cpf_cnpj_titular', 'nome_titular').distinct():
        nodes_dict[t['cpf_cnpj_titular']] = t['nome_titular']
    for t in transacoes.values('cpf_cnpj_od', 'nome_pessoa_od').distinct():
        if t['cpf_cnpj_od'] not in nodes_dict:
            nodes_dict[t['cpf_cnpj_od']] = t['nome_pessoa_od']

    # Agrupa as transações por natureza
    links_query = transacoes.values('cpf_cnpj_titular', 'cpf_cnpj_od', 'natureza_lancamento').annotate(
        value=Sum('valor_transacao')
    ).order_by('cpf_cnpj_titular', 'cpf_cnpj_od')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="vinculos_bancarios_{caso_ativo.numero}.csv"'
    response.write(u'\ufeff'.encode('utf8')) # BOM for Excel

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['CPF/CNPJ Origem', 'Nome Origem', 'CPF/CNPJ Destino', 'Nome Destino', 'Natureza', 'Valor Total'])

    for link in links_query:
        cpf_origem = link['cpf_cnpj_titular']
        cpf_destino = link['cpf_cnpj_od']
        natureza = 'Crédito' if link.get('natureza_lancamento') == 'C' else 'Débito'
        writer.writerow([
            cpf_origem,
            nodes_dict.get(cpf_origem, 'N/A'),
            cpf_destino,
            nodes_dict.get(cpf_destino, 'N/A'),
            natureza,
            f"{link['value']:.2f}".replace('.', ',')
        ])

    return response

@login_required
def calendario(request):
    return render(request, 'bancaria/calendario.html')

@login_required
def calendario_eventos(request):
    # Para cada data e pessoa, calcular crédito e débito
    eventos = ExtratoDetalhado.objects.values('data_lancamento', 'nome_titular').annotate(
        total_credito=Sum(Case(When(natureza_lancamento='C', then='valor_transacao'), default=Value(0), output_field=FloatField())),
        total_debito=Sum(Case(When(natureza_lancamento='D', then='valor_transacao'), default=Value(0), output_field=FloatField()))
    ).order_by('data_lancamento', 'nome_titular')

    eventos_formatados = []
    for evento in eventos:
        data = evento['data_lancamento']
        nome = evento['nome_titular']
        eventos_formatados.append({
            'title': f"Crédito: {moeda(evento['total_credito'])} | Débito: {moeda(evento['total_debito'])}<br>{nome}",
            'start': data.strftime('%Y-%m-%d'),
            'extendedProps': {
                'titulares': nome,
            }
        })

    return JsonResponse(eventos_formatados, safe=False)


@login_required
def transacoes_dia(request):
    data_str = request.GET.get('data')
    if not data_str:
        return JsonResponse({'data': [], 'pessoas': []})

    data = datetime.strptime(data_str, '%Y-%m-%d').date()
    
    # Agrupa transações por pessoa
    pessoas = ExtratoDetalhado.objects.filter(data_lancamento=data).values(
        'nome_titular', 'cpf_cnpj_titular'
    ).annotate(
        total_credito=Sum(Case(When(natureza_lancamento='C', then=F('valor_transacao')), default=0, output_field=FloatField())),
        total_debito=Sum(Case(When(natureza_lancamento='D', then=F('valor_transacao')), default=0, output_field=FloatField())),
        total_transacoes=Count('id')
    ).order_by('-total_credito', '-total_debito')
    
    # Saldo do dia para cada pessoa
    for i, pessoa in enumerate(pessoas):
        pessoas[i]['saldo'] = moeda(pessoas[i]['total_credito'] - pessoas[i]['total_debito'])
    
    # Todas as transações para a tabela
    transacoes = ExtratoDetalhado.objects.filter(data_lancamento=data).values(
        'nome_titular',
        'cpf_cnpj_titular',
        'descricao_lancamento',
        'valor_transacao',
        'natureza_lancamento',
        'nome_pessoa_od',
        'cpf_cnpj_od',
    )
    
    return JsonResponse({
        'data': list(transacoes),
        'pessoas': list(pessoas)
    })

@login_required
def analise_vinculos_selecionados(request):
    caso_ativo = Caso.objects.filter(ativo=True).first()
    if not caso_ativo:
        messages.error(request, 'Nenhum caso ativo encontrado.')
        return redirect('casos:index')

    # Obtém lista única de titulares
    titulares = ExtratoDetalhado.objects.filter(
        caso=caso_ativo
    ).values(
        'cpf_cnpj_titular', 'nome_titular'
    ).distinct().order_by('nome_titular')

    if request.method == 'POST':
        # Obtém os titulares e contrapartes selecionados
        titulares_selecionados = request.POST.getlist('titulares[]')
        contrapartes_selecionadas = request.POST.getlist('contrapartes[]')

        # Filtra os registros que atendem aos critérios
        registros = ExtratoDetalhado.objects.filter(
            caso=caso_ativo,
            cpf_cnpj_titular__in=titulares_selecionados,
            cpf_cnpj_od__in=contrapartes_selecionadas
        ).select_related('cooperacao')

        return JsonResponse({
            'data': list(registros.values(
                'data_lancamento',
                'nome_titular',
                'cpf_cnpj_titular',
                'nome_pessoa_od',
                'cpf_cnpj_od',
                'descricao_lancamento',
                'valor_transacao',
                'natureza_lancamento',
                'cooperacao__numero'
            ))
        })

    # Para AJAX: buscar contrapartes de um titular específico
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'GET':
        print("[DEBUG] Requisição AJAX recebida")
        titular_cpf = request.GET.get('titular_cpf')
        print(f"[DEBUG] CPF do titular recebido: {titular_cpf}")
        
        if titular_cpf:
            contrapartes = ExtratoDetalhado.objects.filter(
                caso=caso_ativo,
                cpf_cnpj_titular=titular_cpf
            ).values(
                'cpf_cnpj_od', 'nome_pessoa_od'
            ).distinct().order_by('nome_pessoa_od')
            
            contrapartes_list = list(contrapartes)
            print(f"[DEBUG] Contrapartes encontradas: {len(contrapartes_list)}")
            print(f"[DEBUG] Primeira contraparte: {contrapartes_list[0] if contrapartes_list else None}")
            
            return JsonResponse({'contrapartes': contrapartes_list})

    context = {
        'title': 'Análise de Vínculos Selecionados',
        'subtitle': f'Caso: {caso_ativo.numero}',
        'titulares': titulares,
    }
    
    return render(request, 'bancaria/analise_vinculos_selecionados.html', context)

@login_required
def analise_ia_vinculos(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)

    try:
        caso_ativo = Caso.objects.filter(ativo=True).first()
        if not caso_ativo:
            return JsonResponse({'success': False, 'error': 'Nenhum caso ativo encontrado'}, status=400)

        # Obtém os titulares e contrapartes selecionados
        titulares_selecionados = request.POST.getlist('titulares[]')
        contrapartes_selecionadas = request.POST.getlist('contrapartes[]')

        if not titulares_selecionados or not contrapartes_selecionadas:
            return JsonResponse({'success': False, 'error': 'Selecione pelo menos um titular e uma contraparte'}, status=400)

        # Filtra os registros que atendem aos critérios
        registros = ExtratoDetalhado.objects.filter(
            caso=caso_ativo,
            cpf_cnpj_titular__in=titulares_selecionados,
            cpf_cnpj_od__in=contrapartes_selecionadas
        ).select_related('cooperacao')

        if not registros.exists():
            return JsonResponse({'success': False, 'error': 'Nenhum registro encontrado para análise'}, status=400)

        # Obtém ou cria o prompt
        from financeira.models import Prompt
        prompt_obj, created = Prompt.objects.get_or_create(
            modulo='bancaria',
            funcao='analise_vinculos',
            label='Análise de Movimentação Bancária',
            defaults={
                'prompt': 'Faça uma análise da movimentação bancária',
                'description': 'Análise de movimentações bancárias entre titulares e contrapartes selecionados',
                'parameters': {
                    'titulares': 'Lista de CPFs/CNPJs dos titulares',
                    'contrapartes': 'Lista de CPFs/CNPJs das contrapartes',
                    'registros': 'Dados das transações'
                },
                'created_by': request.user
            }
        )

        # Prepara os dados para a IA
        dados_analise = {
            'titulares': list(registros.values('cpf_cnpj_titular', 'nome_titular').distinct()),
            'contrapartes': list(registros.values('cpf_cnpj_od', 'nome_pessoa_od').distinct()),
            'registros': list(registros.values(
                'data_lancamento',
                'nome_titular',
                'cpf_cnpj_titular',
                'nome_pessoa_od',
                'cpf_cnpj_od',
                'descricao_lancamento',
                'valor_transacao',
                'natureza_lancamento'
            ))
        }

        # Calcula estatísticas
        total_transacoes = len(dados_analise['registros'])
        total_valor = sum(r['valor_transacao'] for r in dados_analise['registros'])
        creditos = sum(r['valor_transacao'] for r in dados_analise['registros'] if r['natureza_lancamento'] == 'C')
        debitos = sum(r['valor_transacao'] for r in dados_analise['registros'] if r['natureza_lancamento'] == 'D')

        # Monta o prompt para a IA
        prompt_content = f"""
{prompt_obj.prompt}

Dados para análise:
- Período: {dados_analise['registros'][0]['data_lancamento']} a {dados_analise['registros'][-1]['data_lancamento']}
- Total de transações: {total_transacoes}
- Valor total movimentado: R$ {total_valor:,.2f}
- Total de créditos: R$ {creditos:,.2f}
- Total de débitos: R$ {debitos:,.2f}

Titulares envolvidos: {len(dados_analise['titulares'])}
Contrapartes envolvidas: {len(dados_analise['contrapartes'])}

Detalhes das transações:
{json.dumps(dados_analise['registros'], indent=2, default=str)}

Por favor, faça uma análise detalhada dessas movimentações bancárias, identificando padrões, possíveis irregularidades e insights relevantes para investigação.
"""

        # Executa a análise com IA
        from utils.ia import executar_prompt
        analise = executar_prompt([
            {"role": "user", "content": prompt_content}
        ])

        if analise:
            return JsonResponse({
                'success': True,
                'analise': analise
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Erro ao executar análise com IA'
            })

    except Exception as e:
        print(f"Erro na análise com IA: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }, status=500)


@login_required
def detalhes_pessoa(request):
    """
    View para mostrar detalhes completos das movimentações bancárias de uma pessoa
    """
    try:
        cpf = request.GET.get('cpf')
        nome = request.GET.get('nome', '')
        
        if not cpf:
            return JsonResponse({'error': 'CPF não fornecido'}, status=400)
        
        # Obtém o caso ativo
        caso_ativo = Caso.objects.filter(ativo=True).first()
        if not caso_ativo:
            return JsonResponse({'error': 'Nenhum caso ativo encontrado'}, status=400)
        
        # Busca todas as transações onde a pessoa aparece como titular ou contraparte
        transacoes_titular = ExtratoDetalhado.objects.filter(
            caso=caso_ativo,
            cpf_cnpj_titular=cpf
        ).select_related('cooperacao')
        
        transacoes_contraparte = ExtratoDetalhado.objects.filter(
            caso=caso_ativo,
            cpf_cnpj_od=cpf
        ).select_related('cooperacao')
        
        # Combina e ordena todas as transações
        todas_transacoes = list(transacoes_titular) + list(transacoes_contraparte)
        todas_transacoes.sort(key=lambda x: x.data_lancamento, reverse=True)
        
        # Calcula estatísticas
        total_transacoes = len(todas_transacoes)
        total_valor = sum(t.valor_transacao for t in todas_transacoes)
        creditos = sum(t.valor_transacao for t in todas_transacoes if t.natureza_lancamento == 'C')
        debitos = sum(t.valor_transacao for t in todas_transacoes if t.natureza_lancamento == 'D')
        
        # Agrupa transações por titular
        transacoes_por_titular = {}
        for transacao in todas_transacoes:
            titular_key = f"{transacao.cpf_cnpj_titular}_{transacao.nome_titular}"
            if titular_key not in transacoes_por_titular:
                transacoes_por_titular[titular_key] = {
                    'cpf_cnpj': transacao.cpf_cnpj_titular,
                    'nome': transacao.nome_titular,
                    'banco': transacao.banco,
                    'agencia': transacao.numero_agencia,
                    'conta': transacao.numero_conta,
                    'transacoes': [],
                    'creditos': 0,
                    'debitos': 0,
                    'total': 0
                }
            transacoes_por_titular[titular_key]['transacoes'].append(transacao)
        
        # Calcula estatísticas para cada titular
        for titular_key, titular_data in transacoes_por_titular.items():
            creditos_titular = sum(t.valor_transacao for t in titular_data['transacoes'] if t.natureza_lancamento == 'C')
            debitos_titular = sum(t.valor_transacao for t in titular_data['transacoes'] if t.natureza_lancamento == 'D')
            total_titular = creditos_titular - debitos_titular
            
            transacoes_por_titular[titular_key]['creditos'] = creditos_titular
            transacoes_por_titular[titular_key]['debitos'] = debitos_titular
            transacoes_por_titular[titular_key]['saldo'] = total_titular
        
        # Prepara dados para gráficos
        dados_grafico = {
            'labels': ['Créditos', 'Débitos'],
            'datasets': [{
                'label': 'Valores (R$)',
                'data': [creditos, debitos],
                'backgroundColor': ['#28a745', '#dc3545'],
                'borderColor': ['#28a745', '#dc3545'],
                'borderWidth': 1
            }]
        }
        
        # Dados para gráfico de linha (movimentação ao longo do tempo)
        transacoes_por_data = {}
        for transacao in todas_transacoes:
            data_str = transacao.data_lancamento.strftime('%Y-%m-%d')
            if data_str not in transacoes_por_data:
                transacoes_por_data[data_str] = {'creditos': 0, 'debitos': 0}
            
            if transacao.natureza_lancamento == 'C':
                transacoes_por_data[data_str]['creditos'] += transacao.valor_transacao
            else:
                transacoes_por_data[data_str]['debitos'] += transacao.valor_transacao
        
        # Ordena as datas
        datas_ordenadas = sorted(transacoes_por_data.keys())
        dados_linha = {
            'labels': datas_ordenadas,
            'datasets': [
                {
                    'label': 'Créditos',
                    'data': [transacoes_por_data[data]['creditos'] for data in datas_ordenadas],
                    'borderColor': '#28a745',
                    'backgroundColor': 'rgba(40, 167, 69, 0.1)',
                },
                {
                    'label': 'Débitos',
                    'data': [transacoes_por_data[data]['debitos'] for data in datas_ordenadas],
                    'borderColor': '#dc3545',
                    'backgroundColor': 'rgba(220, 53, 69, 0.1)',
                }
            ]
        }
        
        context = {
            'pessoa': {
                'cpf_cnpj': cpf,
                'nome': nome,
                'total_transacoes': total_transacoes,
                'total_valor': total_valor,
                'creditos': creditos,
                'debitos': debitos,
                'saldo': creditos - debitos
            },
            'transacoes_por_titular': transacoes_por_titular,
            'todas_transacoes': todas_transacoes,
            'dados_grafico': dados_grafico,
            'dados_linha': dados_linha,
            'title': f'Detalhes - {nome}',
            'subtitle': f'CPF/CNPJ: {cpf}'
        }
        
        return render(request, 'bancaria/detalhes_pessoa.html', context)
        
    except Exception as e:
        print(f"Erro ao buscar detalhes da pessoa: {e}")
        return JsonResponse({
            'error': f'Erro interno: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def analise_ia_detalhes_pessoa(request):
    """
    Endpoint para análise com IA dos detalhes de uma pessoa
    """
    try:
        # Verifica se é uma requisição AJAX
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Requisição inválida'}, status=400)
        
        # Obtém os dados do request
        data = json.loads(request.body)
        cpf_cnpj = data.get('cpf_cnpj')
        nome = data.get('nome')
        
        if not cpf_cnpj or not nome:
            return JsonResponse({'success': False, 'error': 'CPF/CNPJ e nome são obrigatórios'}, status=400)
        
        # Busca todas as transações da pessoa (como titular ou contraparte)
        todas_transacoes = ExtratoDetalhado.objects.filter(
            Q(cpf_cnpj_titular=cpf_cnpj) | Q(cpf_cnpj_od=cpf_cnpj)
        ).select_related('cooperacao').order_by('data_lancamento')
        
        if not todas_transacoes.exists():
            return JsonResponse({'success': False, 'error': 'Nenhuma transação encontrada para esta pessoa'}, status=404)
        
        # Calcula estatísticas gerais
        total_transacoes = todas_transacoes.count()
        total_valor = sum(t.valor_transacao for t in todas_transacoes)
        creditos = sum(t.valor_transacao for t in todas_transacoes if t.natureza_lancamento == 'C')
        debitos = sum(t.valor_transacao for t in todas_transacoes if t.natureza_lancamento == 'D')
        saldo = creditos - debitos
        
        # Agrupa transações por titular
        transacoes_por_titular = {}
        for transacao in todas_transacoes:
            titular_key = f"{transacao.cpf_cnpj_titular}_{transacao.nome_titular}"
            if titular_key not in transacoes_por_titular:
                transacoes_por_titular[titular_key] = {
                    'cpf_cnpj': transacao.cpf_cnpj_titular,
                    'nome': transacao.nome_titular,
                    'banco': transacao.banco,
                    'agencia': transacao.numero_agencia,
                    'conta': transacao.numero_conta,
                    'transacoes': [],
                    'creditos': 0,
                    'debitos': 0,
                    'saldo': 0
                }
            transacoes_por_titular[titular_key]['transacoes'].append(transacao)
        
        # Calcula estatísticas para cada titular
        for titular_key, titular_data in transacoes_por_titular.items():
            creditos_titular = sum(t.valor_transacao for t in titular_data['transacoes'] if t.natureza_lancamento == 'C')
            debitos_titular = sum(t.valor_transacao for t in titular_data['transacoes'] if t.natureza_lancamento == 'D')
            total_titular = creditos_titular - debitos_titular
            
            transacoes_por_titular[titular_key]['creditos'] = creditos_titular
            transacoes_por_titular[titular_key]['debitos'] = debitos_titular
            transacoes_por_titular[titular_key]['saldo'] = total_titular
        
        # Prepara dados para a IA
        dados_analise = {
            'pessoa': {
                'nome': nome,
                'cpf_cnpj': cpf_cnpj,
                'total_transacoes': total_transacoes,
                'total_valor': total_valor,
                'creditos': creditos,
                'debitos': debitos,
                'saldo': saldo
            },
            'contas_bancarias': transacoes_por_titular,
            'transacoes': []
        }
        
        # Adiciona algumas transações representativas (máximo 20)
        for transacao in todas_transacoes[:20]:
            dados_analise['transacoes'].append({
                'data': transacao.data_lancamento.strftime('%d/%m/%Y'),
                'descricao': transacao.descricao_lancamento,
                'valor': transacao.valor_transacao,
                'natureza': 'Crédito' if transacao.natureza_lancamento == 'C' else 'Débito',
                'titular': transacao.nome_titular,
                'contraparte': transacao.nome_pessoa_od if transacao.nome_pessoa_od else 'N/A'
            })
        
        # Busca ou cria o prompt
        from financeira.models import Prompt
        prompt_obj, created = Prompt.objects.get_or_create(
            modulo="bancaria",
            funcao="detalhes_pessoa",
            label="Análise Detalhada de Movimentação Bancária",
            defaults={
                'prompt': 'Faça uma análise detalhada da movimentação bancária da pessoa, incluindo padrões de comportamento, possíveis irregularidades, e insights relevantes para investigação.',
                'description': 'Análise completa dos dados bancários de uma pessoa específica',
                'created_by': request.user
            }
        )
        
        # Prepara o conteúdo do prompt
        prompt_content = f"""
        Analise os dados bancários da pessoa {nome} (CPF/CNPJ: {cpf_cnpj}).

        DADOS GERAIS:
        - Total de transações: {total_transacoes}
        - Valor total movimentado: R$ {total_valor:,.2f}
        - Total de créditos: R$ {creditos:,.2f}
        - Total de débitos: R$ {debitos:,.2f}
        - Saldo: R$ {saldo:,.2f}

        CONTAS BANCÁRIAS:
        {json.dumps(transacoes_por_titular, indent=2, default=str)}

        TRANSAÇÕES REPRESENTATIVAS:
        {json.dumps(dados_analise['transacoes'], indent=2, default=str)}

        Por favor, faça uma análise detalhada incluindo:
        1. Padrões de comportamento financeiro
        2. Possíveis irregularidades ou pontos de atenção
        3. Relacionamentos com outras pessoas/empresas
        4. Insights relevantes para investigação
        5. Recomendações de próximos passos

        Use formatação markdown para melhor apresentação.
        """
        
        # Executa o prompt
        from utils.ia import executar_prompt
        messages = [
            {"role": "system", "content": prompt_obj.prompt},
            {"role": "user", "content": prompt_content}
        ]
        resultado = executar_prompt(messages)
        
        return JsonResponse({
            'success': True,
            'analise': resultado
        })
        
    except Exception as e:
        print(f"Erro na análise IA dos detalhes da pessoa: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Erro interno: {str(e)}'
        }, status=500)

@login_required
def filtrar_extrato_titular(request):
    """
    View para filtrar extratos por titular e intervalo de datas
    """
    if request.method == 'GET':
        # Obtém todos os titulares únicos
        titulares = ExtratoDetalhado.objects.values(
            'cpf_cnpj_titular', 'nome_titular'
        ).distinct().order_by('nome_titular')
        
        # Obtém as datas mínima e máxima para o slider
        from django.db import models
        datas = ExtratoDetalhado.objects.aggregate(
            data_min=models.Min('data_lancamento'),
            data_max=models.Max('data_lancamento')
        )
        
        # Converte as datas para timestamps Unix (milissegundos)
        import time
        data_min_timestamp = int(time.mktime(datas['data_min'].timetuple()) * 1000) if datas['data_min'] else 0
        data_max_timestamp = int(time.mktime(datas['data_max'].timetuple()) * 1000) if datas['data_max'] else 0
        
        context = {
            'titulares': titulares,
            'data_min': datas['data_min'],
            'data_max': datas['data_max'],
            'data_min_timestamp': data_min_timestamp,
            'data_max_timestamp': data_max_timestamp,
            'title': 'Filtrar Extrato por Titular',
            'subtitle': 'Selecione um titular e intervalo de datas para visualizar os registros'
        }
        
        return render(request, 'bancaria/filtrar_extrato_titular.html', context)
    
    elif request.method == 'POST':
        try:
            cpf_cnpj_titular = request.POST.get('cpf_cnpj_titular')
            data_inicio = request.POST.get('data_inicio')
            data_fim = request.POST.get('data_fim')
            
            print(f"DEBUG - cpf_cnpj_titular: {cpf_cnpj_titular}")
            print(f"DEBUG - data_inicio: {data_inicio}")
            print(f"DEBUG - data_fim: {data_fim}")
            
            if not cpf_cnpj_titular or not data_inicio or not data_fim:
                return JsonResponse({
                    'success': False,
                    'error': 'Todos os campos são obrigatórios'
                }, status=400)
            
            # Converte as datas
            from datetime import datetime
            try:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
                print(f"DEBUG - data_inicio convertida: {data_inicio}")
                print(f"DEBUG - data_fim convertida: {data_fim}")
            except ValueError as e:
                print(f"DEBUG - Erro ao converter datas: {e}")
                return JsonResponse({
                    'success': False,
                    'error': f'Formato de data inválido: {data_inicio} ou {data_fim}'
                }, status=400)
            
            # Filtra os registros
            registros = ExtratoDetalhado.objects.filter(
                cpf_cnpj_titular=cpf_cnpj_titular,
                data_lancamento__range=[data_inicio, data_fim]
            ).order_by('data_lancamento')
            
            # Calcula totais
            from django.db import models
            creditos = registros.filter(natureza_lancamento='C').aggregate(
                total=models.Sum('valor_transacao')
            )['total'] or 0
            
            debitos = registros.filter(natureza_lancamento='D').aggregate(
                total=models.Sum('valor_transacao')
            )['total'] or 0
            
            saldo = creditos - debitos
            
            # Prepara dados para a tabela
            dados_tabela = []
            for registro in registros:
                dados_tabela.append({
                    'id': registro.id,
                    'data': registro.data_lancamento.strftime('%d/%m/%Y'),
                    'descricao': registro.descricao_lancamento,
                    'valor': registro.valor_transacao,
                    'natureza': 'Crédito' if registro.natureza_lancamento == 'C' else 'Débito',
                    'saldo': registro.valor_saldo,
                    'documento': registro.numero_documento,
                    'contraparte': registro.nome_pessoa_od or '-',
                    'cpf_cnpj_od': registro.cpf_cnpj_od or '',
                    'nome_pessoa_od': registro.nome_pessoa_od or '',
                    'banco': registro.banco or '-',
                    'agencia': registro.numero_agencia or '-',
                    'conta': registro.numero_conta or '-'
                })
            
            return JsonResponse({
                'success': True,
                'registros': dados_tabela,
                'totais': {
                    'creditos': creditos,
                    'debitos': debitos,
                    'saldo': saldo,
                    'total_registros': len(dados_tabela)
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }, status=500)


# -----------------------------
# CHAT COM DADOS (IA + QUERY)
# -----------------------------
@login_required
def chat_dados(request):
    """
    Interface de chat onde o usuário envia um prompt em linguagem natural.
    O sistema converte o prompt em filtros (JSON) a partir do schema do modelo `ExtratoDetalhado`,
    executa a consulta, e roda uma segunda análise por IA para explicar os resultados.
    """
    context = {
        'title': 'Chat com Dados - Análise Bancária',
        'subtitle': 'Pergunte em linguagem natural; o sistema consulta o banco e explica os resultados.',
        'analise_markdown_html': '',
        'registros': [],
        'erro': None,
        'prompt_usuario': '',
        'filtros_json': None,
        # KPIs (valores e strings formatadas)
        'kpi_total': 0.0,
        'kpi_creditos': 0.0,
        'kpi_debitos': 0.0,
        'kpi_saldo': 0.0,
        'kpi_total_str': moeda(0.0),
        'kpi_creditos_str': moeda(0.0),
        'kpi_debitos_str': moeda(0.0),
        'kpi_saldo_str': moeda(0.0),
    }

    if request.method == 'POST':
        prompt_usuario = request.POST.get('prompt', '').strip()
        context['prompt_usuario'] = prompt_usuario

        if not prompt_usuario:
            context['erro'] = 'Informe um prompt.'
            return render(request, 'bancaria/chat_dados.html', context)

        # 1) Pedir à IA para gerar filtros JSON válidos baseados no schema do modelo
        schema_extrato = {
            'campos': [
                'banco', 'numero_agencia', 'numero_conta', 'tipo', 'nome_titular', 'cpf_cnpj_titular',
                'descricao_lancamento', 'cnab', 'data_lancamento', 'numero_documento',
                'numero_documento_transacao', 'local_transacao', 'valor_transacao',
                'natureza_lancamento', 'valor_saldo', 'natureza_saldo', 'cpf_cnpj_od', 'nome_pessoa_od',
                'tipo_pessoa_od', 'numero_banco_od', 'numero_agencia_od', 'numero_conta_od',
                'observacao', 'nome_endossante_cheque', 'doc_endossante_cheque'
            ],
            'tipos': {
                'data_lancamento': 'date (YYYY-MM-DD)',
                'valor_transacao': 'number',
                'valor_saldo': 'number',
                'natureza_lancamento': "string ('C' ou 'D')",
                'natureza_saldo': "string ('C' ou 'D')"
            },
            'observacoes': [
                'Use somente chaves válidas do modelo.',
                'Para intervalos de data use data_lancamento__range: [YYYY-MM-DD, YYYY-MM-DD].',
                'Para comparações use sufixos Django: __gte, __lte, __icontains, etc.',
                'Responda SOMENTE com um JSON válido de filtros. Sem texto adicional.'
            ]
        }

        system_msg = (
            'Você converte perguntas em linguagem natural sobre movimentações bancárias '
            'em um JSON de filtros para Django ORM. Não explique, apenas retorne o JSON.'
        )
        user_msg = (
            f"Prompt do usuário: {prompt_usuario}\n\n"
            f"Schema do modelo ExtratoDetalhado: {json.dumps(schema_extrato, ensure_ascii=False)}\n\n"
            "Gere um JSON de filtros (chave->valor) para ser usado em ExtratoDetalhado.objects.filter(**filtros)."
        )

        filtros_json_texto = executar_prompt([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ]) or '{}'

        # Sanitiza e tenta converter em JSON
        try:
            # Extrai bloco JSON se a IA retornar algo a mais
            inicio = filtros_json_texto.find('{')
            fim = filtros_json_texto.rfind('}')
            filtros_json_texto = filtros_json_texto[inicio:fim+1] if inicio != -1 and fim != -1 else '{}'
            filtros = json.loads(filtros_json_texto)
        except Exception:
            filtros = {}

        # 2) Construir queryset de forma segura (permitir apenas campos conhecidos)
        campos_permitidos = {
            'banco', 'numero_agencia', 'numero_conta', 'tipo', 'nome_titular', 'cpf_cnpj_titular',
            'descricao_lancamento', 'cnab', 'data_lancamento', 'numero_documento',
            'numero_documento_transacao', 'local_transacao', 'valor_transacao', 'natureza_lancamento',
            'valor_saldo', 'natureza_saldo', 'cpf_cnpj_od', 'nome_pessoa_od', 'tipo_pessoa_od',
            'numero_banco_od', 'numero_agencia_od', 'numero_conta_od', 'observacao',
            'nome_endossante_cheque', 'doc_endossante_cheque'
        }

        filtros_seguro = {}
        for chave, valor in (filtros.items() if isinstance(filtros, dict) else []):
            campo_base = chave.split('__')[0]
            if campo_base in campos_permitidos:
                filtros_seguro[chave] = valor

        # Limitar ao caso ativo (se existir) para contexto
        caso_ativo = None
        try:
            caso_ativo = Caso.objects.filter(ativo=True).first()
        except Exception:
            pass

        queryset = ExtratoDetalhado.objects.all()
        if caso_ativo:
            queryset = queryset.filter(caso=caso_ativo)

        try:
            registros_qs = queryset.filter(**filtros_seguro).order_by('-data_lancamento')[:500]
        except Exception as e:
            context['erro'] = f'Erro na consulta com os filtros gerados: {e}'
            return render(request, 'bancaria/chat_dados.html', context)

        registros = list(registros_qs.values(
            'data_lancamento', 'nome_titular', 'cpf_cnpj_titular', 'descricao_lancamento',
            'valor_transacao', 'natureza_lancamento', 'nome_pessoa_od', 'cpf_cnpj_od',
            'banco', 'numero_agencia', 'numero_conta'
        ))

        context['registros'] = registros
        context['filtros_json'] = filtros_seguro

        # 3) Rodar segunda análise por IA em Markdown sobre os resultados
        try:
            total = len(registros)
            total_creditos = float(sum(r['valor_transacao'] for r in registros if r['natureza_lancamento'] == 'C'))
            total_debitos = float(sum(r['valor_transacao'] for r in registros if r['natureza_lancamento'] == 'D'))
            saldo = float(total_creditos - total_debitos)
            volume_total = float(total_creditos + total_debitos)

            # Preencher KPIs no contexto
            context['kpi_total'] = volume_total
            context['kpi_creditos'] = total_creditos
            context['kpi_debitos'] = total_debitos
            context['kpi_saldo'] = saldo
            context['kpi_total_str'] = moeda(volume_total)
            context['kpi_creditos_str'] = moeda(total_creditos)
            context['kpi_debitos_str'] = moeda(total_debitos)
            context['kpi_saldo_str'] = moeda(saldo)

            analise_prompt = f"""
Você é um perito em análise bancária. Explique, em Markdown, o que mostram esses resultados da consulta.

Resumo pré-calculado:
- Total de registros: {total}
- Total de créditos: {total_creditos:.2f}
- Total de débitos: {total_debitos:.2f}
- Saldo (C - D): {saldo:.2f}

Amostra dos dados (máx. 50 primeiros registros):
{json.dumps(registros[:50], ensure_ascii=False, default=str)}

Requisitos:
- Use títulos, listas e trechos de código Markdown onde fizer sentido
- Liste os KPIs calculados
- Liste os Titulares
- Destaque padrões e potenciais anomalias
- Sugira próximos passos investigativos
"""

            analise_markdown = executar_prompt([
                {"role": "system", "content": "Responda somente em Markdown válido."},
                {"role": "user", "content": analise_prompt}
            ]) or ''

            # Converter Markdown -> HTML usando lib já presente (markdown==3.7)
            import markdown as md
            analise_html = md.markdown(analise_markdown, extensions=[
                'extra', 'tables', 'sane_lists', 'toc'
            ])
            context['analise_markdown_html'] = mark_safe(analise_html)
        except Exception as e:
            context['erro'] = f'Erro ao interpretar os dados com IA: {e}'

    return render(request, 'bancaria/chat_dados.html', context)