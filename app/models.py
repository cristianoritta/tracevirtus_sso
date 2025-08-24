from django.db import models
from django.conf import settings

########################################################################
#
# TABELAS QUE SERVEM VÁRIOS MÓDULOS
#
########################################################################

class Banco(models.Model):
    id = models.AutoField(primary_key=True)
    ispb = models.CharField(max_length=254)
    nome_reduzido = models.TextField() # CSV com vários nomes para compatibilização
    nome = models.CharField(max_length=254)
    codigo_compensacao = models.IntegerField()
    site = models.CharField(max_length=254)
    email = models.CharField(max_length=254)
    outras_informacoes = models.TextField() # JSON com email, telefone, endereço etc

    def __str__(self):
        return f"{self.codigo_compensacao} - {self.nome}"

    class Meta:
        verbose_name = 'Banco'
        verbose_name_plural = 'Bancos'

class Agencia(models.Model):
    id = models.AutoField(primary_key=True)
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

    def __str__(self):
        return f"{self.banco.nome} - {self.agencia} - {self.nome_agencia}"

    class Meta:
        verbose_name = 'Agência'
        verbose_name_plural = 'Agências'



########################################################################
#
# TABELAS DO MÓDULO DE CASOS
#
########################################################################
class Caso(models.Model):
    STATUS_CHOICES = [
        ('andamento', 'Em Andamento'),
        ('encerrada', 'Encerrada'),
    ]

    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=200)
    numero = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='andamento')
    resumo = models.TextField()
    ativo = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.numero} - {self.nome}"

    class Meta:
        verbose_name = 'Caso'
        verbose_name_plural = 'Casos'
    
    def save(self, *args, **kwargs):
        # Se este caso está sendo definido como ativo
        if self.ativo:
            # Desativa todos os outros casos
            Caso.objects.exclude(id=self.id).update(ativo=False)
        super().save(*args, **kwargs)

class Investigado(models.Model):
    TIPO_CHOICES = [
        ('fisica', 'Física'),
        ('juridica', 'Jurídica'),
    ]

    id = models.AutoField(primary_key=True)
    nome = models.TextField()
    cpf_cnpj = models.IntegerField(unique=True)
    tipo = models.CharField(max_length=254, choices=TIPO_CHOICES)
    dados_pessoais = models.TextField()
    enderecos = models.TextField()
    observacoes = models.TextField()

    def __str__(self):
        return f"{self.cpf_cnpj} - {self.nome}"

    class Meta:
        verbose_name = 'Investigado'
        verbose_name_plural = 'Investigados'

class CasoInvestigado(models.Model):
    """Relacionamento Many-to-Many entre Caso e Investigado"""
    id = models.AutoField(primary_key=True)
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name='investigados')
    investigado = models.ForeignKey(Investigado, on_delete=models.CASCADE, related_name='casos')
    data_inclusao = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.caso.numero} - {self.investigado.nome}"

    class Meta:
        verbose_name = 'CasoInvestigado'
        verbose_name_plural = 'CasosInvestigados'
        unique_together = ('caso', 'investigado')  # Evita duplicação

class Arquivo(models.Model):
    id = models.AutoField(primary_key=True)
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE)
    external_id = models.IntegerField()
    tipo = models.CharField(max_length=254)
    nome = models.CharField(max_length=254)
    hash = models.CharField(max_length=254)
    registros = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.caso.numero} - {self.nome}"

    class Meta:
        verbose_name = 'Arquivo'
        verbose_name_plural = 'Arquivos'




########################################################################
#
# TABELAS DO MÓDULO DE RELATÓRIOS
#
########################################################################
class Relatorio(models.Model):
    TIPO_CHOICES = [
        ('financeiro', 'Financeiro'),
        ('bancaria', 'Bancária'),
        ('patrimonial', 'Patrimonial'),
    ]
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
    ]

    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=254)
    descricao = models.TextField()
    tipo = models.CharField(max_length=254, choices=TIPO_CHOICES)
    status = models.CharField(max_length=254, choices=STATUS_CHOICES)
    arquivo = models.FileField(upload_to='relatorios/')
    historico_atualizacoes = models.JSONField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nome} - {self.tipo} - {self.status}"

    class Meta:
        verbose_name = 'Relatório'
        verbose_name_plural = 'Relatórios'
