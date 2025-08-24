from django.core.management.base import BaseCommand
from financeira.models import Prompt
from user.models import CustomUser


class Command(BaseCommand):
    help = 'Popula o banco de dados com prompts padrão'

    def handle(self, *args, **options):
        # Buscar um usuário para ser o criador dos prompts
        user = CustomUser.objects.first()
        if not user:
            self.stdout.write(
                self.style.ERROR('Nenhum usuário encontrado. Crie um usuário primeiro.')
            )
            return

        # Prompt para análise de comunicação
        prompt_comunicacao, created = Prompt.objects.get_or_create(
            modulo='financeira',
            funcao='comunicacao_detalhes',
            label='Análise das informações adicionais da Comunicação',
            defaults={
                'prompt': """Organize os dados da comunicação financeira a seguir. Faça uma análise que contemple:
1. Informações pessoais sobre o cadastrado (Cadastro, Profissão, sócio de empresa, renda/salário, Know Yout Client - KYC):
2. Período analisado:
3. Movimentações a crédito (também chamado de Origem dos recursos):
4. Movimentações a débito (destino dos recursos):
5. Caracteristicas das movimentações financeiras:
6. Outras informações relevantes:

<comunicacao>
{comunicacao}
</comunicacao>""",
                'description': 'Análise detalhada das informações adicionais de uma comunicação financeira',
                'parameters': '{"comunicacao": "string"}',
                'is_active': True,
                'created_by': user
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS('Prompt de análise de comunicação criado com sucesso!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Prompt de análise de comunicação já existe.')
            )

        # Prompt para análise de ocorrência
        prompt_ocorrencia, created = Prompt.objects.get_or_create(
            modulo='financeira',
            funcao='ocorrencia_ajuda',
            label='Análise de Ocorrência COAF',
            defaults={
                'prompt': """Você é um especialista em investigação financeira e lavagem de dinheiro. Explique o que significa na prática, e com exemplos, essas tipificacoes da Lavagem do Dinheiro informadas pelo COAF: {ocorrencia}. O nome do titular é {titular}, o CPF/CNPJ é {cpf_cnpj}, a agência é {agencia} e a conta é {conta}.""",
                'description': 'Análise de ocorrências do COAF para explicar tipificações de lavagem de dinheiro',
                'parameters': '{"ocorrencia": "string", "titular": "string", "cpf_cnpj": "string", "agencia": "string", "conta": "string"}',
                'is_active': True,
                'created_by': user
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS('Prompt de análise de ocorrência criado com sucesso!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Prompt de análise de ocorrência já existe.')
            )

        # Prompt para análise de informações adicionais
        prompt_info_adicional, created = Prompt.objects.get_or_create(
            modulo='financeira',
            funcao='informacoes_adicionais',
            label='Análise de Informações Adicionais',
            defaults={
                'prompt': """Você é um especialista em investigação financeira e lavagem de dinheiro. Identifique, no texto, os envolvidos (nome e cpf/cnpj) o tipo de transação (crédito, débito) o valor (R$) e a quantidade. O Campo plataforma pode ser 'PIX', 'Depósito', 'Transferência' ou outras referência que você encontrar - se não encontrar algo explicito, deixe em branco. <texto>{texto}</texto>. 
                ATENÇÃO. A sua resposta deve ser um objeto json [{{'nome': 'nome', 'cpf_cnpj': 'cpf/cnpj', 'tipo_transacao': 'tipo', 'valor': 'valor', 'quantidade': 'quantidade', 'plataforma': ''}}]. Não de nenhuma explicação, apenas o objeto json.""",
                'description': 'Extrai informações estruturadas de texto de informações adicionais',
                'parameters': '{"texto": "string"}',
                'is_active': True,
                'created_by': user
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS('Prompt de análise de informações adicionais criado com sucesso!')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Prompt de análise de informações adicionais já existe.')
            )

        self.stdout.write(
            self.style.SUCCESS('População de prompts concluída!')
        ) 