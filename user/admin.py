from django.contrib import admin
from .models import (
    Planos, Assinatura, CustomUser, CategoriaInstituicao, 
    Instituicao, Cargo, UFs, Cidades, UserLogs, TermosUso
)

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('cpf', 'nome_completo', 'email', 'telefone', 'instituicao', 'cargo', 'cidade')
    list_filter = ('instituicao', 'cargo', 'uf_residencia')
    search_fields = ('nome_completo', 'cpf', 'email', 'telefone')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('nome_completo',)

@admin.register(CategoriaInstituicao)
class CategoriaInstituicaoAdmin(admin.ModelAdmin):
    list_display = ('categoria_instituicao', 'created_at', 'updated_at')
    search_fields = ('categoria_instituicao',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Instituicao)
class InstituicaoAdmin(admin.ModelAdmin):
    list_display = ('instituicao', 'categoria_instituicao', 'created_at', 'updated_at')
    list_filter = ('categoria_instituicao',)
    search_fields = ('instituicao',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('cargo', 'categoria_instituicao', 'created_at', 'updated_at')
    list_filter = ('categoria_instituicao',)
    search_fields = ('cargo',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UFs)
class UFsAdmin(admin.ModelAdmin):
    list_display = ('uf', 'sigla_uf', 'codigo_uf')
    search_fields = ('uf', 'sigla_uf', 'codigo_uf')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Cidades)
class CidadesAdmin(admin.ModelAdmin):
    list_display = ('cidade', 'uf', 'cod_ibge', 'capital', 'ddd')
    list_filter = ('sigla_uf', 'capital')
    search_fields = ('cidade', 'cod_ibge')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(UserLogs)
class UserLogsAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'ip', 'porta', 'device', 'created_at')
    list_filter = ('device',)
    search_fields = ('usuario__nome_completo', 'ip', 'log')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(TermosUso)
class TermosUsoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'app', 'versaodotermo', 'aceite', 'ip', 'created_at')
    list_filter = ('app', 'aceite', 'versaodotermo')
    search_fields = ('usuario__nome_completo', 'ip')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
