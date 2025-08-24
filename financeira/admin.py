from django.contrib import admin
from .models import RIF, Comunicacao, Envolvido, Ocorrencia, InformacaoAdicional, KYC, ComunicacaoNaoProcessada, Prompt

# Register your models here.

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ['modulo', 'funcao', 'label', 'is_active', 'created_by', 'created_at', 'updated_at']
    list_filter = ['modulo', 'funcao', 'is_active', 'created_at']
    search_fields = ['label', 'prompt', 'description']
    readonly_fields = ['created_at', 'updated_at', 'old_versions']
    fieldsets = (
        ('Identificação', {
            'fields': ('modulo', 'funcao', 'label', 'is_active')
        }),
        ('Conteúdo', {
            'fields': ('prompt', 'description', 'parameters')
        }),
        ('Controle', {
            'fields': ('created_by', 'created_at', 'updated_at', 'old_versions'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Se é uma criação
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
