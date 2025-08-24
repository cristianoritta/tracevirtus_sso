from django.urls import path
from . import views

app_name = 'bancaria'

urlpatterns = [
    path('', views.index, name='index'),
    path('index/', views.index, name='index_alt'),
    path('chat-dados/', views.chat_dados, name='chat_dados'),
    path('cooperacao/<int:id>/delete/', views.delete_cooperacao, name='delete_cooperacao'),
    path('importar-arquivos/', views.importar_arquivos, name='importar_arquivos'),
    path('relatorio/', views.gerar_relatorio_bancario, name='gerar_relatorio'),
    path('arquivos/<int:cooperacao_id>/', views.listar_arquivos, name='listar_arquivos'),
    path('arquivo/<int:id>/delete/', views.delete_arquivo, name='delete_arquivo'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('extratodetalhado/', views.extrato_detalhado, name='extrato_detalhado'),
    path('extrato_detalhado/<int:cooperacao_id>/', views.extrato_detalhado, name='extrato_detalhado'),
    path('unificardados/', views.unificar_dados, name='unificar_dados'),
    path('titulares/<int:cooperacao_id>/', views.listar_titulares, name='listar_titulares'),
    
    path('analisedevinculos/', views.analise_de_vinculos, name='analise_de_vinculos'),
    path('analisedevinculos/download_csv', views.download_vinculos_csv, name='download_vinculos_csv'),
    
    path('calendario/', views.calendario, name='calendario'),
    path('calendario/eventos/', views.calendario_eventos, name='calendario_eventos'),
    path('calendario/transacoes_dia/', views.transacoes_dia, name='transacoes_dia'),
    path('analise-vinculos-selecionados/', views.analise_vinculos_selecionados, name='analise_vinculos_selecionados'),
    path('analise-ia-vinculos/', views.analise_ia_vinculos, name='analise_ia_vinculos'),
    path('detalhes-pessoa/', views.detalhes_pessoa, name='detalhes_pessoa'),
    path('analise-ia-detalhes-pessoa/', views.analise_ia_detalhes_pessoa, name='analise_ia_detalhes_pessoa'),
    path('filtrar-extrato-titular/', views.filtrar_extrato_titular, name='filtrar_extrato_titular'),
] 