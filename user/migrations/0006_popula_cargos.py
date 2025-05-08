from django.db import migrations
import csv
import os

def popula_cargos(apps, schema_editor):
    Cargo = apps.get_model('user', 'Cargo')
    CategoriaInstituicao = apps.get_model('user', 'CategoriaInstituicao')

    arquivo_csv = os.path.join('user', 'dados', 'cargos.csv')
    
    with open(arquivo_csv, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for linha in reader:
            categoria = CategoriaInstituicao.objects.get(id=int(linha['id_categoria_instituicao']))
            cargo = {
                'id': int(linha['id']),
                'cargo': linha['cargo'],
                'categoria_instituicao': categoria
            }
            Cargo.objects.create(**cargo)

class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_popula_instituicoes'),
    ]

    operations = [
        migrations.RunPython(popula_cargos),
    ]
