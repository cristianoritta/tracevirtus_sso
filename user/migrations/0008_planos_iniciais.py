from django.db import migrations

def criar_planos(apps, schema_editor):
    Planos = apps.get_model('user', 'Planos')
    
    # Plano Gratuito
    Planos.objects.create(
        nome='Gratuito',
        faces=50,
        reconhecimentos=250,
        valor_regular=0,
        valor_promocional=0,
        periodo=3,
        publico=False
    )
    
    # Plano Premium Trimestral
    Planos.objects.create(
        nome='Premium Trimestral',
        faces=7500,
        reconhecimentos=7500,
        valor_regular=288.00,
        valor_promocional=120.00,
        periodo=90,
        publico=True
    )
    
    # Plano Premium Mensal
    Planos.objects.create(
        nome='Premium Mensal',
        faces=2500,
        reconhecimentos=2500,
        valor_regular=96.00,
        valor_promocional=96.00,
        periodo=30,
        publico=True
    )

def remover_planos(apps, schema_editor):
    Planos = apps.get_model('user', 'Planos')
    Planos.objects.filter(nome__in=['Gratuito', 'Premium Trimestral', 'Premium Mensal']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('user', '0007_popula_ufs'),
    ]

    operations = [
        migrations.RunPython(criar_planos, remover_planos),
    ] 