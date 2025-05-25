from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('casos/', views.casos, name='casos'),
    path('casos/index', views.casos),
    path('casos/novo/', views.novo_caso, name='novo_caso'),
    path('casos/<int:id>/', views.editar_caso, name='editar_caso'),
    path('casos/<int:id>/excluir/', views.excluir_caso, name='excluir_caso'),
    path('casos/<int:id>/ativo/', views.caso_ativo, name='caso_ativo'),
    path('casos/<int:id>/investigados/', views.investigados, name='investigados'),
    
    # URLs para investigados
    path('casos/<int:caso_id>/investigados/adicionar/', views.adicionar_investigado, name='adicionar_investigado'),
    path('casos/<int:caso_id>/investigados/<int:investigado_id>/editar/', views.editar_investigado, name='editar_investigado'),
    path('casos/<int:caso_id>/investigados/<int:investigado_id>/detalhes/', views.detalhes_investigado, name='detalhes_investigado'),
    path('casos/<int:caso_id>/investigados/<int:investigado_id>/remover/', views.remover_investigado, name='remover_investigado'),
    path('casos/<int:id>/investigados/<int:investigado_id>/excluir/', views.excluir_investigado, name='excluir_investigado'),
    path('investigados/<int:investigado_id>/excluir/', views.excluir_investigado, name='excluir_investigado'),
    path('api/buscar-investigado/', views.buscar_investigado, name='buscar_investigado'),
]

