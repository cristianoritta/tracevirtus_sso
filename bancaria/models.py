from django.db import models

# Create your models here.
class Banco(models.Model):
    ispb = models.CharField(max_length=254)
    nome_reduzido = models.TextField()
    nome = models.CharField(max_length=254)
    codigo_compensacao = models.IntegerField()
    site = models.CharField(max_length=254)
    email = models.CharField(max_length=254)
    outras_informacoes = models.TextField()

    def __str__(self):
        return self.nome

class BancoAgencia(models.Model):
    banco = models.ForeignKey(Banco, on_delete=models.CASCADE)
    agencia = models.CharField(max_length=254)
    nome_agencia = models.CharField(max_length=254)
    endereco = models.CharField(max_length=254)
    numero = models.CharField(max_length=50)
    complemento = models.CharField(max_length=254)
    bairro = models.CharField(max_length=254)
    cep = models.CharField(max_length=9)
    municipio = models.CharField(max_length=254)
    uf = models.CharField(max_length=2)
    telefone = models.CharField(max_length=20)
    email = models.CharField(max_length=254)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"{self.banco.nome} - {self.agencia}"


class Cooperacao(models.Model):
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE, related_name='cooperacoes_bancarias')
    numero = models.CharField(max_length=254)
    inquerito = models.CharField(max_length=254)
    processo = models.CharField(max_length=254)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cooperação {self.numero}"


class ExtratoDetalhado(models.Model):
    NATUREZA_CHOICES = [
        ('C', 'Crédito'),
        ('D', 'Débito')
    ]

    cooperacao = models.ForeignKey('Cooperacao', on_delete=models.CASCADE)
    caso = models.ForeignKey('app.Caso', on_delete=models.CASCADE)
    arquivo = models.ForeignKey('app.Arquivo', on_delete=models.CASCADE)
    banco = models.CharField(max_length=10, blank=True)
    numero_agencia = models.CharField(max_length=20, blank=True)
    numero_conta = models.CharField(max_length=20, blank=True)
    tipo = models.CharField(max_length=10, blank=True)
    nome_titular = models.CharField(max_length=254)
    cpf_cnpj_titular = models.CharField(max_length=254)
    descricao_lancamento = models.CharField(max_length=254)
    cnab = models.CharField(max_length=254)
    data_lancamento = models.DateField()
    numero_documento = models.CharField(max_length=254)
    numero_documento_transacao = models.CharField(max_length=254)
    local_transacao = models.CharField(max_length=254)
    valor_transacao = models.FloatField()
    natureza_lancamento = models.CharField(max_length=10)
    valor_saldo = models.FloatField()
    natureza_saldo = models.CharField(max_length=1, choices=NATUREZA_CHOICES)
    cpf_cnpj_od = models.CharField(max_length=254)
    nome_pessoa_od = models.CharField(max_length=254)
    tipo_pessoa_od = models.CharField(max_length=254)
    numero_banco_od = models.CharField(max_length=10, blank=True)
    numero_agencia_od = models.CharField(max_length=20, blank=True)
    numero_conta_od = models.CharField(max_length=20, blank=True)
    observacao = models.CharField(max_length=254)
    nome_endossante_cheque = models.CharField(max_length=254)
    doc_endossante_cheque = models.CharField(max_length=254)

    def __str__(self):
        return f"Extrato {self.id} - {self.nome_titular}"
