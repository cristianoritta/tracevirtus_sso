from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_superuser(apps, schema_editor):
    CustomUser = apps.get_model('user', 'CustomUser')
    
    # Criar superusuários
    superuser1 = CustomUser.objects.create(
        username='alvarolucasno',
        email='alvarolucasno@gmail.com',
        data_nascimento='1990-01-01',
        telefone='79991637026',
        uf_residencia='SE',
        password=make_password('123456'),
        nome_completo='Alvaro Lucas Nascimento de Oliveira',
        cpf='04884452569',
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )

    superuser2 = CustomUser.objects.create(
        username='cristianoritta',
        email='tiano.ritta@gmail.com',
        data_nascimento='1990-01-01',
        telefone='53999270103',
        uf_residencia='RS',
        password=make_password('123456'),
        nome_completo='Cristiano Ritta',
        cpf='00383038090',
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )

def reverse_superuser(apps, schema_editor):
    CustomUser = apps.get_model('user', 'CustomUser')
    CustomUser.objects.filter(username__in=['alvarolucasno', 'cristianoritta']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_superuser, reverse_superuser),
    ]