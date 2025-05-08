from django.urls import path
from . import views

urlpatterns = [
    #ROTA DE COMPLETAR CADASTRO
    path('completar-cadastro/', views.completar_cadastro, name='completar_cadastro'),

    #ROTAS AJAX
    path('ajax/instituicao/', views.ajax_instituicao, name='instituicao_ajax'),
    path('ajax/cargo/', views.ajax_cargo, name='cargo_ajax'),
    path('ajax/cidade/', views.ajax_cidade, name='cidade_ajax'),
    path('ajax/usuarios/', views.ajax_usuarios, name='usuarios_ajax'),

    #ROTA DE ADMIN
    path('logs/', views.logs, name='logs'),

    #ROTA DE USUÁRIO
    path('dados/', views.dados_usuario, name='dados_usuario'),
]
