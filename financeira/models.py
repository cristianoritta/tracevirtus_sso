from django.db import models

class Cooperacao(models.Model):
    id = models.AutoField(primary_key=True)
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE)
    numero = models.CharField(max_length=254)
    inquerito = models.CharField(max_length=254)
    processo = models.CharField(max_length=254)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.caso.numero} - {self.numero}"

    class Meta:
        verbose_name = 'Cooperacao'
        verbose_name_plural = 'Cooperacoes'

class RIF(models.Model):
    id = models.AutoField(primary_key=True)
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE)
    numero = models.CharField(max_length=254)
    outras_informacoes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.caso.numero} - {self.numero}"

    class Meta:
        verbose_name = 'RIF'
        verbose_name_plural = 'RIFs'

class Comunicacao(models.Model):
    id = models.AutoField(primary_key=True)
    rif = models.ForeignKey(RIF, on_delete=models.CASCADE)
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE)
    arquivo = models.ForeignKey('app.Arquivo', on_delete=models.CASCADE)
    indexador = models.IntegerField()
    id_comunicacao = models.IntegerField()                      # número de referência da comunicação no sistema do Coaf (Siscoaf).
    numero_ocorrencia_bc = models.CharField(max_length=254)     # número de referência da comunicação no sistema do Comunicante.
    data_recebimento = models.CharField(max_length=254)         # registra a data e hora em que a comunicação foi recebida pelo Siscoaf.    
    data_operacao = models.CharField(max_length=254)            # data inicial da análise da movimentação financeira feita pelo comunicante.
    data_fim_fato = models.CharField(max_length=254)            # data final da análise da movimentação financeira feita pelo comunicante.
    cpf_cnpj_comunicante = models.IntegerField()                # CPF/CNPJ do Comunicante.
    nome_comunicante = models.CharField(max_length=254)         # nome da Instituição Financeira/Obrigado legal que fez a comunicação.
    cidade_agencia = models.CharField(max_length=254)           # cidade da agência bancária a que pertence a conta bancária objeto da comunicação, quando aplicável.
    uf_agencia = models.CharField(max_length=2)                 # UF da agência bancária a que pertence a conta bancária objeto da comunicação, quando aplicável.
    nome_agencia = models.CharField(max_length=254)             # agência bancária a que pertence a conta bancária objeto da comunicação, quando aplicável.
    numero_agencia = models.IntegerField()                      # código da agência bancária ou sufixo do CNPJ correspondente da agência bancária a que pertence a conta bancária objeto da comunicação, quando aplicável.
    informacoes_adicionais = models.TextField()                 # Campo que traz o registro do fato ou fenômeno suspeito identificado pelo comunicante. Normalmente traz as seguintes informações:
                                                                    #    o Informações cadastrais do titular da conta, bem como sua renda ou faturamento declarado.
                                                                    #    o Resumo das movimentações a crédito, informando as características da movimentação financeira (utilização de cheques, TEDs, transferências eletrônicas, dinheiro em espécie, etc).
                                                                    #    o Relação dos principais remetentes de recursos, na opinião do comunicante.
                                                                    #    o Resumo das movimentações a débito, informando as características da movimentação financeira.
                                                                    #    o Relação dos principais destinatários de recursos, na opinião do comunicante.
                                                                    #    o Informações de Conheça seu Cliente ou Know your Client (KYC), cujo principal objetivo é identificar o comportamento do titular da conta. Pode trazer indícios da prática de ilícitos, notícias de mídia, informações de diligências realizadas pelo comunicante, entre outros.
    campo_a = models.TextField()                                # campo A
    campo_b = models.TextField()                                # campo B
    campo_c = models.TextField()                                # campo C
    campo_d = models.TextField()                                # campo D
    campo_e = models.TextField()                                # campo E
    codigo_segmento = models.IntegerField()                     # registra o segmento da economia que realizou a comunicação.

    def __str__(self):
        return f"{self.caso.numero} - {self.id_comunicacao}"

    class Meta:
        verbose_name = 'Comunicacaoo'
        verbose_name_plural = 'Comunicacoes'

class Envolvido(models.Model):
    id = models.AutoField(primary_key=True)
    rif = models.ForeignKey(RIF, on_delete=models.CASCADE)
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE)
    arquivo = models.ForeignKey('app.Arquivo', on_delete=models.CASCADE)
    indexador = models.IntegerField()
    cpf_cnpj_envolvido = models.IntegerField()
    nome_envolvido = models.CharField(max_length=254)
    tipo_envolvido = models.CharField(max_length=254)
    agencia_envolvido = models.IntegerField()
    conta_envolvido = models.IntegerField()
    data_abertura_conta = models.DateField()
    data_atualizacao_conta = models.DateField()
    bit_pep_citado = models.CharField(max_length=3)
    bit_pessoa_obrigada_citado = models.CharField(max_length=3)
    int_servidor_citado = models.CharField(max_length=3)

    def __str__(self):
        return f"{self.caso.numero} - {self.nome_envolvido}"

    class Meta:
        verbose_name = 'Envolvido'
        verbose_name_plural = 'Envolvidos'

class Ocorrencia(models.Model):
    id = models.AutoField(primary_key=True)
    rif = models.ForeignKey(RIF, on_delete=models.CASCADE)
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE)
    arquivo = models.ForeignKey('app.Arquivo', on_delete=models.CASCADE)
    indexador = models.IntegerField()
    id_ocorrencia = models.IntegerField()
    ocorrencia = models.TextField()

    def __str__(self):
        return f"{self.caso.numero} - {self.id_ocorrencia}"

    class Meta:
        verbose_name = 'Ocorrencia'
        verbose_name_plural = 'Ocorrencias'

class InformacaoAdicional(models.Model):
    id = models.AutoField(primary_key=True)
    rif = models.ForeignKey(RIF, on_delete=models.CASCADE)
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE)
    arquivo = models.ForeignKey('app.Arquivo', on_delete=models.CASCADE)
    comunicacao = models.ForeignKey(Comunicacao, on_delete=models.CASCADE)
    indexador = models.IntegerField()
    tipo_transacao = models.IntegerField()
    cpf = models.IntegerField()
    nome = models.TextField()
    valor = models.FloatField()
    transacoes = models.IntegerField()
    plataforma = models.CharField(max_length=254)

    def __str__(self):
        return f"{self.caso.numero} - {self.nome}"

    class Meta:
        verbose_name = 'InformacaoAdicional'
        verbose_name_plural = 'InformacoesAdicionais'

class KYC(models.Model):
    id = models.AutoField(primary_key=True)
    rif = models.ForeignKey(RIF, on_delete=models.CASCADE)
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE)
    arquivo = models.ForeignKey('app.Arquivo', on_delete=models.CASCADE)
    comunicacao = models.ForeignKey(Comunicacao, on_delete=models.CASCADE)
    indexador = models.IntegerField()
    profissao = models.CharField(max_length=254)
    renda = models.FloatField()
    periodo = models.CharField(max_length=254)
    analise = models.TextField()

    def __str__(self):
        return f"{self.caso.numero} - {self.profissao}"

    class Meta:
        verbose_name = 'KYC'
        verbose_name_plural = 'KYCs'

class Plugin(models.Model):
    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=12)
    nome = models.TextField()
    arquivo = models.TextField()

    def __str__(self):
        return f"{self.tipo} - {self.nome}"

    class Meta:
        verbose_name = 'Plugin'
        verbose_name_plural = 'Plugins'

class ComunicacaoNaoProcessada(models.Model):
    id = models.AutoField(primary_key=True)
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE)
    rif = models.ForeignKey(RIF, on_delete=models.CASCADE)
    arquivo = models.ForeignKey('app.Arquivo', on_delete=models.CASCADE)
    indexador = models.IntegerField()
    nome_comunicante = models.TextField()

    def __str__(self):
        return f"{self.caso.numero} - {self.nome_comunicante}"

    class Meta:
        verbose_name = 'ComunicacaoNaoProcessada'
        verbose_name_plural = 'ComunicacoesNaoProcessadas'
