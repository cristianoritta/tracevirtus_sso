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
    path('analisedevinculos/', views.financeira_analisedevinculos,
         name='financeira_analisedevinculos'),
    path('dashboard/', views.financeira_dashboard, name='financeira_dashboard'),
    path('errosimportacao/', views.financeira_errosimportacao,
         name='financeira_errosimportacao'),

    path('cadastrar_rif/', views.cadastrar_rif, name='cadastrar_rif'),
    path('excluir_rif/<int:rif_id>/', views.excluir_rif, name='excluir_rif'),
    path('importar_arquivos/', views.importar_arquivos, name='importar_arquivos'),
    path('listar_rifs/', views.listar_rifs, name='listar_rifs'),
    
    path('ajuda/<int:id>/', views.ocorrencia_ajuda, name='ocorrencia_ajuda'),
    
    path('envolvido_detalhes/<str:cpf_cnpj>/', views.envolvido_detalhes, name='envolvido_detalhes'),

    path('relatorio', views.relatorio, name='relatorio'),

]
