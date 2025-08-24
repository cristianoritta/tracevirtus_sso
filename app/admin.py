from django.contrib import admin

# Register your models here.
from .models import Caso, Arquivo, Banco, Agencia, Relatorio

admin.site.register(Caso)
admin.site.register(Arquivo)
admin.site.register(Banco)
admin.site.register(Agencia)

@admin.register(Relatorio)
class RelatorioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'status', 'created_by', 'created_at']
    list_filter = ['tipo', 'status', 'created_at']
    search_fields = ['nome', 'descricao']
    readonly_fields = ['created_by', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao', 'tipo', 'status')
        }),
        ('Arquivo', {
            'fields': ('arquivo',)
        }),
        ('Metadados', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Histórico', {
            'fields': ('historico_atualizacoes',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Se é uma criação
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
