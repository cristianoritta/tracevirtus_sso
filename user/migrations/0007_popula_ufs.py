from django.db import migrations
import csv
import os

def popula_ufs(apps, schema_editor):
    UFs = apps.get_model('user', 'UFs')
    
    # Caminho do arquivo CSV
    csv_path = os.path.join('user', 'dados', 'tabela_cidades_banco.csv')
    
    # Dicionário para armazenar UFs únicas
    ufs_unicas = {}
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            codigo_uf = row['codigo_uf']
            
            # Verifica se já processamos esta UF
            if codigo_uf not in ufs_unicas:
                ufs_unicas[codigo_uf] = {
                    'uf': row['uf'],
                    'sigla_uf': row['sigla_uf'],
                    'codigo_uf': codigo_uf
                }
    
    # Cria os registros de UF
    for uf_data in ufs_unicas.values():
        UFs.objects.create(
            uf=uf_data['uf'],
            sigla_uf=uf_data['sigla_uf'],
            codigo_uf=uf_data['codigo_uf']
        )

class Migration(migrations.Migration):

    dependencies = [
        ('user', '0006_popula_cargos'),
    ]

    operations = [
        migrations.RunPython(popula_ufs),
    ]
