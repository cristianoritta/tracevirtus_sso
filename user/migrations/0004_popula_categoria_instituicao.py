from django.db import migrations

def popula_categoria_instituicao(apps, schema_editor):
    CategoriaInstituicao = apps.get_model('user', 'CategoriaInstituicao')
    
    CategoriaInstituicao.objects.all().delete()
    CategoriaInstituicao.objects.create(id=1, categoria_instituicao='Polícia Civil')
    CategoriaInstituicao.objects.create(id=2, categoria_instituicao='Polícia Federal')
    CategoriaInstituicao.objects.create(id=3, categoria_instituicao='Polícia Militar')
    CategoriaInstituicao.objects.create(id=4, categoria_instituicao='Polícia Rodoviária Federal')
    CategoriaInstituicao.objects.create(id=5, categoria_instituicao='Guarda Municipal')
    CategoriaInstituicao.objects.create(id=6, categoria_instituicao='Exército Brasileiro')
    CategoriaInstituicao.objects.create(id=7, categoria_instituicao='Marinha do Brasil')
    CategoriaInstituicao.objects.create(id=8, categoria_instituicao='Força Aérea Brasileira')
    CategoriaInstituicao.objects.create(id=9, categoria_instituicao='Receita Federal')
    CategoriaInstituicao.objects.create(id=10, categoria_instituicao='ABIN')

def reverse_categoria_instituicao(apps, schema_editor):
    CategoriaInstituicao = apps.get_model('user', 'CategoriaInstituicao')
    CategoriaInstituicao.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('user', '0003_popula_cidades'),
    ]

    operations = [
        migrations.RunPython(popula_categoria_instituicao, reverse_categoria_instituicao),
    ]
