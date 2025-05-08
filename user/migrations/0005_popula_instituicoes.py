from django.db import migrations
import csv
import os

def popula_instituicoes(apps, schema_editor):
    Instituicao = apps.get_model('user', 'Instituicao')
    CategoriaInstituicao = apps.get_model('user', 'CategoriaInstituicao')
    
    # Obtém o caminho absoluto para o arquivo CSV
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'dados', 'instituicoes.csv')
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file, delimiter=';')
        for row in csv_reader:
            categoria = CategoriaInstituicao.objects.get(id=int(row['categoria_instituicao']))
            Instituicao.objects.create(
                id=int(row['id']),
                instituicao=row['instituicao'],
                categoria_instituicao=categoria
            )

def reverse_popula_instituicoes(apps, schema_editor):
    Instituicao = apps.get_model('user', 'Instituicao')
    Instituicao.objects.all().delete()

class Migration(migrations.Migration):
    dependencies = [
        ('user', '0004_popula_categoria_instituicao'),
    ]

    operations = [
        migrations.RunPython(popula_instituicoes, reverse_popula_instituicoes),
    ]
