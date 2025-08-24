from django.urls import path
from . import views

app_name = 'financeira'

# URLs para Financeira (financeira/urls.py)
urlpatterns = [
    path('index/', views.financeira_index, name='financeira_index'),
    
    path('comunicacoes/', views.financeira_comunicacoes,
         name='financeira_comunicacoes'),
    path('envolvidos/', views.financeira_envolvidos,
         name='financeira_envolvidos'),
    path('ocorrencias/', views.financeira_ocorrencias,
         name='financeira_ocorrencias'),
    path('informacoesadicionais/', views.financeira_informacoesadicionais,
         name='financeira_informacoesadicionais'),
    path('informacoesadicionais/delete/<int:info_id>/', views.informacoes_adicionais_delete,
         name='informacoes_adicionais_delete'),
    path('upload_planilha/', views.upload_planilha, name='upload_planilha'),
    path('download_modelo_planilha/', views.download_modelo_planilha, name='download_modelo_planilha'),
    path('analisedevinculos/', views.financeira_analisedevinculos,
         name='financeira_analisedevinculos'),
    path('analisedevinculos/download_csv/', views.download_vinculos_csv, name='download_vinculos_csv'),
    path('analisedevinculos/download_anx/', views.download_vinculos_anx, name='download_vinculos_anx'),
    path('dashboard/', views.financeira_dashboard, name='financeira_dashboard'),
    path('errosimportacao/', views.financeira_errosimportacao,
         name='financeira_errosimportacao'),
    path('errosimportacao/processar/<int:comunicacao_id>/', views.processar_comunicacao, name='processar_comunicacao'),
    path('errosimportacao/processar/envolvido/<int:comunicacao_id>/<int:envolvido_id>/', views.processar_envolvido_especifico, name='processar_envolvido_especifico'),

    path('cadastrar_rif/', views.cadastrar_rif, name='cadastrar_rif'),
    path('excluir_rif/<int:rif_id>/', views.excluir_rif, name='excluir_rif'),
    path('importar_arquivos/', views.importar_arquivos, name='importar_arquivos'),
    path('listar_rifs/', views.listar_rifs, name='listar_rifs'),
    
    path('ajuda/<int:id>/', views.ocorrencia_ajuda, name='ocorrencia_ajuda'),
    
    path('envolvido_detalhes/<str:cpf_cnpj>/', views.envolvido_detalhes, name='envolvido_detalhes'),
    path('envolvidos/<str:cpf_cnpj_envolvido>/<int:rif_id>/', views.comunicacoes_envolvido, name='comunicacoes_envolvido'),

    path('resumo', views.resumo, name='resumo'),
    path('resumo/<int:caso_id>/', views.resumo_por_id, name='resumo_por_id'),

     path('relatorio_documento', views.relatorio_documento, name='relatorio_documento'),

    # Nova URL para detalhes da comunicação
    path('comunicacao/<int:comunicacao_id>/', views.comunicacao_detalhes, name='comunicacao_detalhes'),

    # URLs para gerenciamento de prompts
    path('prompts/', views.prompts_list, name='prompts_list'),
    path('prompts/create/', views.prompt_create, name='prompt_create'),
    path('prompts/<int:prompt_id>/edit/', views.prompt_edit, name='prompt_edit'),
    path('prompts/<int:prompt_id>/delete/', views.prompt_delete, name='prompt_delete'),
    path('prompts/<int:prompt_id>/toggle/', views.prompt_toggle_active, name='prompt_toggle_active'),
    path('prompts/test/', views.prompts_test, name='prompts_test'),
    
    # Chat
    path('chat/', views.financeira_chat, name='financeira_chat'),
    path('api/chat/', views.financeira_chat_api, name='financeira_chat_api'),

    # Relatórios
    # path('relatorios/', views.financeira_relatorios, name='financeira_relatorios'),

    # Reprocessar comunicação
    path('reprocessar_comunicacao/<int:comunicacao_id>/', views.processar_comunicacao, name='reprocessar_comunicacao'),
    
    # Queries customizadas
    path('custom_queries/', views.custom_queries_dashboard, name='custom_queries_dashboard'),
    path('api/custom_query/', views.execute_custom_query_api, name='execute_custom_query_api'),
    path('api/create_query/', views.create_query_api, name='create_query_api'),
]
