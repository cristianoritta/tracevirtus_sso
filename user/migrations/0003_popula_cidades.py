from django.db import migrations
import csv
import os

def popula_cidades(apps, schema_editor):
    Cidades = apps.get_model('user', 'Cidades')
    
    # Obtém o caminho absoluto para o arquivo CSV
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'dados', 'tabela_cidades_banco.csv')
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            Cidades.objects.create(
                id=int(row['id']),
                cod_ibge=int(row['cod_ibge']),
                cidade=row['cidade'],
                capital=bool(int(row['capital'])),
                codigo_uf=int(row['codigo_uf']),
                sigla_uf=row['sigla_uf'],
                uf=row['uf'],
                ddd=int(row['ddd']),
                fuso_horario=row['fuso_horario'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                siafi_id=int(row['siafi_id'])
            )

def reverse_popula_cidades(apps, schema_editor):
    Cidades = apps.get_model('user', 'Cidades')
    Cidades.objects.all().delete()

class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_create_superuser'),
    ]

    operations = [
        migrations.RunPython(popula_cidades, reverse_popula_cidades),
    ]
