from django.db import models
from django.db import models
from django.contrib.auth.models import AbstractUser
from core.validators import validate_cpf

class CategoriaInstituicao(models.Model):
    categoria_instituicao = models.CharField(max_length=255)
    
    #auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='categoria_instituicao_created_by', to_field='cpf')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='categoria_instituicao_updated_by', to_field='cpf')
    def __str__(self):
        return self.categoria_instituicao


class Instituicao(models.Model):
    instituicao = models.CharField(max_length=255)
    categoria_instituicao = models.ForeignKey(CategoriaInstituicao, on_delete=models.SET_NULL, 
                                              null=True, related_name='instituicao_categoria_instituicao')
    
    #auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='instituicao_created_by', to_field='cpf')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='instituicao_updated_by', to_field='cpf')

    def __str__(self):
        return self.instituicao

class Cargo(models.Model):
    categoria_instituicao = models.ForeignKey(CategoriaInstituicao, on_delete=models.SET_NULL, 
                                              null=True, related_name='cargo_categoria_instituicao')
    cargo = models.CharField(max_length=255)
    
    #auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='cargo_created_by', to_field='cpf')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='cargo_updated_by', to_field='cpf')

    def __str__(self):
        return self.cargo
    
class UFs(models.Model):
    uf = models.CharField(max_length=255)
    sigla_uf = models.CharField(max_length=2)
    codigo_uf = models.CharField(max_length=5)
    
    #auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='uf_created_by', to_field='cpf')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='uf_updated_by', to_field='cpf')

    def __str__(self):
        return self.uf
    
class Cidades(models.Model):
    id = models.IntegerField(primary_key=True)
    cod_ibge = models.IntegerField()
    cidade = models.CharField(max_length=100)
    capital = models.BooleanField()
    codigo_uf = models.IntegerField()
    sigla_uf = models.CharField(max_length=2)
    uf = models.CharField(max_length=100)
    ddd = models.IntegerField()
    fuso_horario = models.CharField(max_length=50)
    latitude = models.FloatField()
    longitude = models.FloatField()
    siafi_id = models.IntegerField()
    
    #auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='cidades_created_by', to_field='cpf')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='cidades_updated_by', to_field='cpf')

    def __str__(self):
        return f'{self.cidade}, {self.uf}'


class CustomUser(AbstractUser):
    nome_completo = models.CharField(max_length=100)
    cpf = models.BigIntegerField(primary_key=True, unique=True, validators=[validate_cpf])
    data_nascimento = models.DateField(null=True, blank=True)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=15)
    instituicao = models.ForeignKey(Instituicao, on_delete=models.SET_NULL, null=True, 
                                    blank=True, related_name='instituicao_usuario')
    cargo = models.ForeignKey(Cargo, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargo_usuario')
    cidade = models.ForeignKey(Cidades, on_delete=models.SET_NULL, null=True, blank=True, related_name='cidade_usuario')
    uf_residencia = models.CharField(max_length=250, null=True, blank=True)
    
    #auditoria 
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='customuser_created_by', to_field='cpf')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='customuser_updated_by', to_field='cpf')

    USERNAME_FIELD = 'cpf'
    REQUIRED_FIELDS = ['username','nome_completo']

    def __str__(self):
        return self.nome_completo
    

class UserLogs(models.Model):
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE, 
                                related_name='logs_usuario', to_field='cpf')
    ip = models.GenericIPAddressField(db_index=True)
    porta = models.IntegerField()
    device = models.CharField(max_length=255, null=True, blank=True)
    log = models.TextField()
    request = models.JSONField()
    
    #auditoria 
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='userlogs_created_by', to_field='cpf')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='userlogs_updated_by', to_field='cpf')
    

class TermosUso(models.Model):
    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE, 
                                related_name='termos_usuario', to_field='cpf')
    ip = models.GenericIPAddressField()
    porta = models.IntegerField(null = True, blank = True)
    app = models.CharField(max_length=255)
    versaodotermo = models.IntegerField()
    aceite = models.BooleanField(default=False)

    #auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='termos_created_by', to_field='cpf')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True
                                   , related_name='termos_updated_by', to_field='cpf')


class Planos(models.Model):
    """
    Modelo para gerenciar os planos disponíveis no sistema.
    """
    nome = models.CharField(max_length=100, help_text="Nome do plano")
    faces = models.IntegerField(help_text="Cota total de faces para o período do plano")
    reconhecimentos = models.IntegerField(help_text="Cota total de reconhecimentos para o período do plano")
    valor_regular = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor do plano")
    valor_promocional = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor promocional do plano")
    periodo = models.IntegerField(help_text="Período em dias")
    publico = models.BooleanField(default=True, help_text="Indica se o plano está disponível publicamente")
    
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                                   to_field='cpf', related_name='planos_created_by')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                                   to_field='cpf', related_name='planos_updated_by')
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Plano'
        verbose_name_plural = 'Planos'
        ordering = ['valor_promocional']
        
    def __str__(self):
        return self.nome

class Assinatura(models.Model):
    """
    Modelo para gerenciar assinaturas e pagamentos dos usuários.
    """
   
    STATUS = (
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
        ('cancelado', 'Cancelado'),
        ('pendente', 'Pendente')
    )
    
    FORMAS_PAGAMENTO = (
        ('pix', 'PIX'),
        ('cartao', 'Cartão de Crédito'),
        ('boleto', 'Boleto')
    )

    usuario = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='assinaturas')
    plano = models.ForeignKey(Planos, on_delete=models.CASCADE, related_name='assinaturas')
    faces = models.IntegerField(help_text="Cota total de faces para o período da assinatura")
    reconhecimentos = models.IntegerField(help_text="Cota total de reconhecimentos para o período da assinatura")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS, default='pendente')
    forma_pagamento = models.CharField(max_length=20, choices=FORMAS_PAGAMENTO, null=True, blank=True)
    
    data_pagamento = models.DateTimeField(null=True, blank=True, help_text="Data em que o pagamento foi confirmado")
    vencimento = models.DateTimeField(null=True, blank=True, help_text="Data de término da assinatura")
    
    id_transacao = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text="ID da transação no gateway de pagamento")
    codigo_fatura = models.CharField(max_length=100, null=True, blank=True, help_text="Código da fatura/boleto")
    json_resposta_transacao = models.JSONField(null=True, blank=True, help_text="JSON da resposta da transação")
    
    validacao_manual = models.BooleanField(default=False, help_text="Indica se a assinatura foi validada manualmente")
    
    created_by = models.BigIntegerField(null=True, blank=True, help_text="ID do usuário proprietário")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_by = models.BigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Assinatura {self.plano} - Usuário {self.usuario} ({self.status})"


    
