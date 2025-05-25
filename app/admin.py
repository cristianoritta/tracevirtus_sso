from django.contrib import admin

# Register your models here.
from .models import Caso, Arquivo, Banco, Agencia

admin.site.register(Caso)
admin.site.register(Arquivo)
admin.site.register(Banco)
admin.site.register(Agencia)
