import re
from jinja2 import Environment, BaseLoader
from typing import List, Dict, Any

class PromptExtractor:
    def __init__(self):
        self.jinja_env = Environment(loader=BaseLoader())
        
    def find_prompts_in_template(self, template_content: str) -> List[Dict[str, Any]]:
        """
        Encontra todos os prompts (### ... ###) no template e identifica
        se estão dentro de blocos de loop do Jinja2
        """
        prompts = []
        
        # Regex para encontrar prompts 
        prompt_pattern = r'{%\s*prompt\s*%}(.*?){%\s*endprompt\s*%}'
        
        # Encontrar todos os prompts
        for match in re.finditer(prompt_pattern, template_content):
            prompt_text = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()
            
            # Verificar se o prompt está dentro de um loop
            loop_info = self._find_containing_loop(template_content, start_pos, end_pos)
            
            prompts.append({
                'prompt': prompt_text,
                'position': (start_pos, end_pos),
                'in_loop': loop_info is not None,
                'loop_info': loop_info,
                'full_match': match.group(0)
            })
            
        return prompts
    
    def _find_containing_loop(self, content: str, start_pos: int, end_pos: int) -> Dict[str, Any]:
        """
        Verifica se uma posição está dentro de um bloco de loop Jinja2
        """
        # Patterns para blocos de loop
        loop_patterns = [
            (r'{%\s*for\s+(\w+)\s+in\s+(\w+(?:\.\w+)*)\s*%}', r'{%\s*endfor\s*%}'),
            (r'{%p\s*for\s+(\w+)\s+in\s+(\w+(?:\.\w+)*)\s*%}', r'{%\s*endfor\s*%}'),
        ]
        
        for open_pattern, close_pattern in loop_patterns:
            # Encontrar todos os blocos de loop
            open_matches = list(re.finditer(open_pattern, content))
            close_matches = list(re.finditer(close_pattern, content))
            
            # Verificar se nossa posição está dentro de algum loop
            for open_match in open_matches:
                loop_start = open_match.end()
                
                # Encontrar o endfor correspondente
                for close_match in close_matches:
                    loop_end = close_match.start()
                    
                    # Verificar se é o endfor correto (depois do for)
                    if loop_end > loop_start:
                        # Verificar se nosso prompt está dentro deste loop
                        if loop_start <= start_pos and end_pos <= loop_end:
                            return {
                                'loop_var': open_match.group(1) if open_match.groups() else None,
                                'loop_collection': open_match.group(2) if len(open_match.groups()) > 1 else None,
                                'loop_start': loop_start,
                                'loop_end': loop_end,
                                'loop_pattern': open_match.group(0)
                            }
                        break
        
        return None
    
    def extract_and_process_prompts(self, template_content: str, context_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Extrai prompts e determina quantas vezes cada um deve ser executado
        baseado no contexto dos dados
        """
        if context_data is None:
            context_data = {}
            
        prompts = self.find_prompts_in_template(template_content)
        processed_prompts = []
        
        for prompt_info in prompts:
            if prompt_info['in_loop']:
                # Prompt está em um loop - precisa ser executado várias vezes
                loop_info = prompt_info['loop_info']
                collection_name = loop_info['loop_collection']
                loop_var = loop_info['loop_var']
                
                # Tentar obter a coleção do contexto
                collection = self._get_nested_value(context_data, collection_name)
                
                if isinstance(collection, (list, tuple)):
                    for i, item in enumerate(collection):
                        # Criar contexto específico para esta iteração
                        iteration_context = context_data.copy()
                        iteration_context[loop_var] = item
                        
                        # Renderizar o prompt com o contexto da iteração
                        rendered_prompt = self._render_prompt_with_context(
                            prompt_info['prompt'], 
                            iteration_context
                        )
                        
                        processed_prompts.append({
                            'original_prompt': prompt_info['prompt'],
                            'rendered_prompt': rendered_prompt,
                            'execution_context': {
                                'loop_var': loop_var,
                                'loop_item': item,
                                'iteration': i,
                                'total_iterations': len(collection)
                            },
                            'in_loop': True,
                            'loop_info': loop_info
                        })
                else:
                    # Coleção não encontrada ou não é iterável
                    processed_prompts.append({
                        'original_prompt': prompt_info['prompt'],
                        'rendered_prompt': prompt_info['prompt'],
                        'execution_context': {'error': f'Collection {collection_name} not found or not iterable'},
                        'in_loop': True,
                        'loop_info': loop_info
                    })
            else:
                # Prompt não está em loop - executa uma vez
                rendered_prompt = self._render_prompt_with_context(
                    prompt_info['prompt'], 
                    context_data
                )
                
                processed_prompts.append({
                    'original_prompt': prompt_info['prompt'],
                    'rendered_prompt': rendered_prompt,
                    'execution_context': {'single_execution': True},
                    'in_loop': False,
                    'loop_info': None
                })
        
        return processed_prompts
    
    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """
        Obtém valor aninhado usando notação de ponto (ex: 'titulares_extratos')
        """
        keys = key_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
                
        return value
    
    def _render_prompt_with_context(self, prompt_template: str, context: Dict[str, Any]) -> str:
        """
        Renderiza o prompt usando Jinja2 com o contexto fornecido
        """
        try:
            template = self.jinja_env.from_string(prompt_template)
            return template.render(**context)
        except Exception as e:
            return f"Erro ao renderizar prompt: {e}"

# Exemplo de uso
def main():
    # Carregando o template
    template_content = """
INQUÉRITO POLICIAL Nº ___
RELATÓRIO TÉCNICO DE INTELIGÊNCIA FINANCEIRA
{% for rif in rifs %}RIF: nº {{rif.numero}}{% endfor %}
O presente Relatório Técnico de Inteligência Financeira foi produzido nos autos do Inquérito Policial acima indicado, da Delegacia de Repressão às Ações Criminosas Organizadas – DRACO Bagé.
A análise de dados realizada através do presente Relatório Técnico de Análise Bancária leva em conta os ditames da Lei nº 9.613, de 3 de março de 1998, no que diz respeito aos registros das transações bancárias disponibilizados pelas instituições financeiras (art. 10 e seguintes). Os dados foram obtidos mediante autorização judicial, nos autos do Inquérito Policial acima mencionado, e transmitidos ao Sistema de Investigação de Movimentações Bancárias (SIMBA) na forma descrita na Carta Circular n.º 3.454/2010 do Banco Central do Brasil – cujos arquivos serão disponibilizados às partes, em anexo.
CONSELHO DE CONTROLE DE ATIVIDADES FINANCEIRAS
O Conselho de Controle de Atividades Financeiras (COAF) é a Unidade de Inteligência Financeira (UIF) do Brasil, a autoridade central do sistema de prevenção e combate à lavagem de dinheiro, ao financiamento do terrorismo e à proliferação de armas de destruição em massa (PLD/FTP), especialmente no recebimento, análise e disseminação de informações de inteligência financeira.
Criado pela Lei nº 9.613, de 3 de março de 1998 (Lei de Lavagem de Dinheiro), e reestruturado pela Lei nº 13.974, de 7 de janeiro de 2020, o COAF é vinculado administrativamente ao Ministério da Fazenda, dotado de autonomia técnica e operacional, e tem atuação em todo o território nacional.
O COAF tem por objetivo prevenir a utilização dos setores econômicos para a lavagem de dinheiro e financiamento do terrorismo, promovendo a cooperação e o intercâmbio de informações entre os setores público e privado e é composto por informações enviadas pelos setores econômicos obrigados (art. 9º da Lei n.º 9.613/98), dentro de regras estabelecidas pelos órgãos reguladores de cada segmento, conforme preceitua o art. 11, §1ª da Lei 9.613/98 (ex: Banco Central e instituições financeiras, SUSEPE com seguradoras privadas, etc.).
O órgão realiza as análises de inteligência financeira decorrentes de comunicações recebidas, de intercâmbio de informações ou de denúncias, e o resultado das análises é registrado no Relatório de Inteligência Financeira (RIF), o qual foi encaminhado à autoridade demandante.
MATERIAL ANALISADO
Para desenvolvimento das análises e elaboração do presente relatório foram utilizadas as informações obtidas junto ao COAF, mediante provocação desse órgão de investigação criminal, a partir de um procedimento de investigação criminal em curso – o Inquérito Policial.
A partir dessa investigação, de onde identificamos provir o dinheiro objeto de lavagem, requisitamos ao COAF a elaboração do(s) relatório(s) de inteligência financeira, que é(são) objeto desta análise:
{% for rif in rifs %}
RIF nº {{rif.numero}}{% endfor %}
Cada RIF é composto por um arquivo em formato PDF e três arquivos em formato CSV contendo informações de comunicações, envolvidos e ocorrências. Esses arquivos foram importados e analisados automaticamente com o uso da Plataforma IAF, onde foram gerados os hashes de verificação dos arquivos, bem como sanitizados os dados. Após, foram processados com outros softwares de análise, como o Trace, I2 e PowerBI. O uso conjunto dessas tecnologias permitiu a produção do presente relatório de forma automatizada, sob supervisão do analista.
Na primeira parte desse relatório foram evidenciados os valores totais a débito e a crédito vinculados aos titulares das contas. Na segunda parte foram detalhadas as movimentações sobre os demais envolvidos (que não são titulares). É importante salientar, nessa segunda parte, que os titulares das contas podem não figurar imediatamente na investigação em curso, mas eles se relacionaram diretamente com um – ou mais – dos investigados, seja recebendo ou enviando dinheiro. Em razão disso, sugerimos a inclusão desses titulares, também, na investigação, a fim de comprovar que a transação financeira pode ter a natureza de lavagem do dinheiro de origem criminosa.
É preciso destacar que as movimentações aqui relacionadas não representam a integralidade das movimentações financeiras envolvendo essas partes, uma vez que as instituições financeiras só são obrigadas a comunicar ao COAF as transações que obedeçam aos critérios legais. Portanto, somente com a quebra do sigilo bancário é que poderão ser identificadas todas as transações financeiras, e o montante de dinheiro transacionados entre cada uma das partes.
CONCEITOS RELEVANTES
Com a finalidade de facilitar a leitura do presente relatório, segue a conceituação de alguns termos:
Comunicação de Operação em Espécie (COE): comunicações encaminhadas automaticamente ao COAF, pelos setores obrigados, quando seus clientes realizam transações em espécie (dinheiro “vivo”) acima de determinado valor estabelecido em norma.
Comunicação de Operação Suspeita (COS): comunicações encaminhadas ao COAF quando entes dos setores obrigados percebem, em transações de seus clientes, suspeitas de lavagem de dinheiro, de financiamento do terrorismo ou de outros ilícitos.
Titular: o proprietário da conta favorecida pelo depósito ou objeto da retirada. O Titular pode ser o próprio suspeito, ou um terceiro, que recebeu ou enviou dinheiro para o investigado.
Remetente: referem-se às pessoas que remeteram (enviaram) valores para a conta comunicada ao COAF, ou seja, são os CRÉDITOS.
Beneficiário: referem-se às pessoas que se beneficiaram (receberam) valores da conta comunicada ao COAF, ou seja, são os DÉBITOS.
Responsável: o proprietário do dinheiro depositado ou o destinatário do dinheiro sacado. Obs.: Esta informação é declarada pelo depositante ou sacador no ato do depósito ou saque.
Depositante: a pessoa que efetuou o depósito.
Sacador: a pessoa que efetuou a retirada.
PEP: pessoa exposta politicamente.
Segmento 41: Movimentações atípicas
Segmento 42: Movimentações em espécie
INFORMAÇÕES GERAIS
Foi realizada a importação dos arquivos do RIF com o uso dos softwares Trace e i2 Analyst’s Notebook, ferramenta que realiza a análise de vínculos entre entidades (pessoas físicas e/ou pessoas jurídicas) que possuam elementos em comum ou que tiveram algum relacionamento. Segue o diagrama geral resultado dessa importação.
AQUI O ANALISTA DEVE INSERIR A VISUALIZAÇÃO DE DADOS DO I2.
Análise de RIF > Exportar Dados
4.1 Movimentações financeiras dos titulares
O gráfico abaixo representa os valores a crédito e a débito movimentados pelos titulares das contas comunicadas (pessoas físicas e pessoas jurídicas). É importante salientar que não está sendo considerado o período em que esse valor foi movimentado, pois, cada comunicação compreende período diverso, os quais serão demonstrados no decorrer do relatório.
< Inserir um gráfico de barras aqui >
ANÁLISE DAS COMUNICAÇÕES POR TITULAR
A análise das comunicações por titular segue a lógica das comunicações do COAF, onde as transações financeiras são reportadas a partir do titular da conta bancária que transacionou com um dos investigados.
Deve ser observado que sobre o titular da conta bancária é que recaem os indicativos legais das transações suspeitas de lavagem de dinheiro e, por eles transacionarem com algum(ns) do(s) investigado(s) é que passam a integrar o rol da presente investigação.
Por conta disso, sugerimos à Autoridade a inclusão das seguintes pessoas nas investigações, com base na análise das suas transações suspeitas:
{%p for alvo in titulares_extratos %}
{{ alvo.nome}}
Ficha Resumo
{%prompt%} Analise as informações do alvo aqui {{alvo.nome}} {%endprompt%}
Foram identificadas as comunicações em que {{alvo.nome}} está relacionado. Ele figura, conforme demostrado na tabela abaixo:
{% if alvo['comunicacoes'] is not none and alvo['comunicacoes']|length > 0 %}
Movimentações de Comunicação Obrigatória ao COAF
As comunicações obrigatórias ao COAF obedecem ao disposto na Carta Circular. São essas em que {{alvo.nome}} consta como titular ou representante:
{% endif %}
Movimentações Suspeitas Reportadas pelo COAF
Segue o gráfico que demonstra as transações suspeitas em que {{alvo.nome}} está relacionado(a).
[ INSIRA UM GRÁFICO DO i2 AQUI ]
{% if alvo[‘outras_informacoes’]|length > 0 %}
As seguintes movimentações suspeitas foram reportadas ao COAF (COS, Cód. 41), de modo exemplificativo. Elas podem ser ampliadas, com a quebra de sigilo bancário.

{{alvo[‘maiorescreditos’]}}
{{alvo[‘maioresdebitos’]}}
{%endif%}
Dos Indícios De Lavagem De Dinheiro (Ocorrências)
Trata-se do enquadramento normativo do órgão regulador que embasou aquela comunicação e que podem configurar indícios de lavagem de dinheiro.
Observações do Analista
Com base na análise do RIF. Identificamos as seguintes informações que são suspeitas de lavagem de capitais:
{{alvo.observacoes_analista}}
{% endfor %}
CONSIDERAÇÕES FINAIS
O presente Relatório buscou esclarecer as informações mais relevantes contidas no(s) Relatório(s) de Inteligência Financeira, bem como identificar indícios do crime de lavagem de dinheiro.
Agora, cabe a Autoridade Policial verificar o relacionamento dessas pessoas com os indivíduos investigados no Inquérito Policial, a fim de aprofundar as investigações sobre as movimentações financeiras. Reiteramos que as comunicações apontadas pelo COAF não esgotam as movimentações financeiras dos investigados e dos envolvidos, de modo que, somente com a quebra do sigilo bancário, fiscal e patrimonial, será possível identificar os verdadeiros montantes de dinheiro circulante.
Destaca-se que todas as informações acima descritas dependem de investigação aprofundada sobre os temas, visto que o Relatório de Inteligência Financeira apenas faz os apontamentos dos indícios de que os valores movimentados são incompatíveis com o patrimônio, a atividade econômica ou ocupação profissional e a capacidade financeira dos envolvidos.
{{ custom_queries }}
ANEXO DE ARQUIVOS
ANEXO DE ENVOLVIDOS
{% for titular in titulares %}
• Titular: {{ titular.nome_envolvido }}
{% for envolvido in titular.envolvidos %}
{{ envolvido.tipo_envolvido }}: {{ envolvido.nome_envolvido }}
{{envolvido.cpf_cnpj_envolvido}}
{% endfor %}
{% endfor %}
Inquérito Policial nº:
<Digite o nº do procedimento>
Data de Instauração:
<Data de instauração>
Crime Investigado:
<Crime investigado>
Suspeitos de Lavagem de Dinheiro:
{% for titular in titulares%}
{{titular.nome_envolvido}}, {{titular.tipo_envolvido}}{% endfor %}

Suspeitos de Lavagem de Dinheiro:
{% for titular in titulares%}
{{titular.nome_envolvido}}, {{titular.tipo_envolvido}}{% endfor %}

Suspeitos de Lavagem de Dinheiro:
{% for titular in titulares%}
{{titular.nome_envolvido}}, {{titular.tipo_envolvido}}{% endfor %}

Titular
Créditos
Débitos
{%tr for alvo in titulares %}
{%tr for alvo in titulares %}
{%tr for alvo in titulares %}
{{alvo.nome_envolvido}}
R$ {{alvo.creditos}}
R$ {{alvo.debitos}}
{%tr endfor %}
Movimentação total:
{{alvo.movimentacao_total}}
Créditos:
{{alvo.creditos}}
Créditos:
{{alvo.creditos}}
Débitos:
{{alvo.debitos}}
Nome:
{{alvo.nome}}
Nome:
{{alvo.nome}}
CPF:
{{alvo.cpf}}
CPF:
{{alvo.cpf}}
Endereço:

Endereço:

Cidade:

Cidade:

Antecedentes Criminais:
{% for antecedente in alvo.antecedentes %}
{{antecedente.data_comunicacao}} | {{antecedente.ocorrencia}} – {{antecedente.fato}} ({{antecedente. participacao}}){% endfor %}

Antecedentes Criminais:
{% for antecedente in alvo.antecedentes %}
{{antecedente.data_comunicacao}} | {{antecedente.ocorrencia}} – {{antecedente.fato}} ({{antecedente. participacao}}){% endfor %}

Antecedentes Criminais:
{% for antecedente in alvo.antecedentes %}
{{antecedente.data_comunicacao}} | {{antecedente.ocorrencia}} – {{antecedente.fato}} ({{antecedente. participacao}}){% endfor %}

Antecedentes Criminais:
{% for antecedente in alvo.antecedentes %}
{{antecedente.data_comunicacao}} | {{antecedente.ocorrencia}} – {{antecedente.fato}} ({{antecedente. participacao}}){% endfor %}

Observações:



Observações:



Observações:



Observações:



Id
CPF/CNPJ Envolvido
Nome Envolvido
Tipo Envolvido
{%tr for comunicacao in alvo.envolvimentos %}
{%tr for comunicacao in alvo.envolvimentos %}
{%tr for comunicacao in alvo.envolvimentos %}
{%tr for comunicacao in alvo.envolvimentos %}
{{comunicacao.Indexador}}
{{comunicacao.cpfCnpjEnvolvido}}
{{comunicacao.nomeEnvolvido}}
{{comunicacao.tipoEnvolvido}}
{%tr endfor %}
{%tr endfor %}
{%tr endfor %}
{%tr endfor %}
Idx
Nome
Segmento
Valor
Descrição
{%tr for informacoes in alvo.comunicacoes_nao_suspeitas%}
{%tr for informacoes in alvo.comunicacoes_nao_suspeitas%}
{%tr for informacoes in alvo.comunicacoes_nao_suspeitas%}
{%tr for informacoes in alvo.comunicacoes_nao_suspeitas%}
{%tr for informacoes in alvo.comunicacoes_nao_suspeitas%}
{{ informacoes.indexador}}
{{informacoes.tipoEnvolvido}}
{{ informacoes.nomeEnvolvido}}
CPF/CNPJ: {{informacoes.cpf}}
{{ informacoes.CodigoSegmento }}
{{ informacoes.CampoA}}
{{ informacoes.informacoesAdicionais}}
{%tr endfor %}
{%tr endfor %}
{%tr endfor %}
{%tr endfor %}
{%tr endfor %}
Idx
Nome
Tipo
Valor
Qtd
Plataforma
{%tr for informacoes in alvo.outras_informacoes %}
{% if informacoes.tipo_transacao == ‘Crédito’ %}
{%tr for informacoes in alvo.outras_informacoes %}
{% if informacoes.tipo_transacao == ‘Crédito’ %}
{%tr for informacoes in alvo.outras_informacoes %}
{% if informacoes.tipo_transacao == ‘Crédito’ %}
{%tr for informacoes in alvo.outras_informacoes %}
{% if informacoes.tipo_transacao == ‘Crédito’ %}
{%tr for informacoes in alvo.outras_informacoes %}
{% if informacoes.tipo_transacao == ‘Crédito’ %}
{%tr for informacoes in alvo.outras_informacoes %}
{% if informacoes.tipo_transacao == ‘Crédito’ %}
{{ informacoes.indexador}}
{{ informacoes.nome}}
CPF/CNPJ: {{informacoes.cpf}}
{{ informacoes.tipo_transacao}}
{{ informacoes.valor}}
{{ informacoes.transacoes}}
{{ informacoes.plataforma}}
{% endif %}{%tr endfor %}
{% endif %}{%tr endfor %}
{% endif %}{%tr endfor %}
{% endif %}{%tr endfor %}
{% endif %}{%tr endfor %}
{% endif %}{%tr endfor %}
Id Ocorrência
Ocorrência
{%tr for ocorrencia in alvo[‘ocorrencias’] %}
{%tr for ocorrencia in alvo[‘ocorrencias’] %}
{{ocorrencia.idOcorrencia}}
{{ocorrencia.ocorrencia}}
{%tr endfor %}
{%tr endfor %}
Arquivo
Hash
{%tr for arquivo in arquivos %}
{{ arquivo.nome }}
{{ arquivo.hash }}
{%tr endfor %}
"""
    
    # Dados de exemplo (você substituiria pelos seus dados reais)
    context_data = {
        'titulares_extratos': [
            {'nome': 'João Silva'},
            {'nome': 'Maria Santos'},
            {'nome': 'Carlos Oliveira'}
        ]
    }
    
    # Criar extrator
    extractor = PromptExtractor()
    
    # Encontrar prompts básicos
    print("=== PROMPTS ENCONTRADOS ===")
    prompts = extractor.find_prompts_in_template(template_content)
    
    for i, prompt in enumerate(prompts):
        print(f"\nPrompt {i+1}:")
        print(f"  Texto: {prompt['prompt']}")
        print(f"  Em loop: {prompt['in_loop']}")
        if prompt['loop_info']:
            print(f"  Loop var: {prompt['loop_info']['loop_var']}")
            print(f"  Loop collection: {prompt['loop_info']['loop_collection']}")
    
    # Processar prompts com contexto
    print("\n\n=== PROMPTS PROCESSADOS ===")
    processed = extractor.extract_and_process_prompts(template_content, context_data)
    
    for i, prompt in enumerate(processed):
        print(f"\nPrompt processado {i+1}:")
        print(f"  Original: {prompt['original_prompt']}")
        print(f"  Renderizado: {prompt['rendered_prompt']}")
        print(f"  Em loop: {prompt['in_loop']}")
        if prompt['in_loop'] and 'iteration' in prompt['execution_context']:
            ctx = prompt['execution_context']
            print(f"  Iteração: {ctx['iteration'] + 1}/{ctx['total_iterations']}")

if __name__ == "__main__":
    main()