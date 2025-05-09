# Generated by Django 5.1.4 on 2025-04-01 21:06

import core.validators
import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('nome_completo', models.CharField(max_length=100)),
                ('cpf', models.BigIntegerField(primary_key=True, serialize=False, unique=True, validators=[core.validators.validate_cpf])),
                ('data_nascimento', models.DateField(blank=True, null=True)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('telefone', models.CharField(max_length=15)),
                ('uf_residencia', models.CharField(blank=True, max_length=250, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customuser_created_by', to=settings.AUTH_USER_MODEL)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='customuser_updated_by', to=settings.AUTH_USER_MODEL)),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Cargo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cargo', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cargo_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cargo_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='customuser',
            name='cargo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cargo_usuario', to='user.cargo'),
        ),
        migrations.CreateModel(
            name='CategoriaInstituicao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('categoria_instituicao', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='categoria_instituicao_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='categoria_instituicao_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='cargo',
            name='categoria_instituicao',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cargo_categoria_instituicao', to='user.categoriainstituicao'),
        ),
        migrations.CreateModel(
            name='Cidades',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('cod_ibge', models.IntegerField()),
                ('cidade', models.CharField(max_length=100)),
                ('capital', models.BooleanField()),
                ('codigo_uf', models.IntegerField()),
                ('sigla_uf', models.CharField(max_length=2)),
                ('uf', models.CharField(max_length=100)),
                ('ddd', models.IntegerField()),
                ('fuso_horario', models.CharField(max_length=50)),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
                ('siafi_id', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cidades_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cidades_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='customuser',
            name='cidade',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cidade_usuario', to='user.cidades'),
        ),
        migrations.CreateModel(
            name='Instituicao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('instituicao', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('categoria_instituicao', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='instituicao_categoria_instituicao', to='user.categoriainstituicao')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='instituicao_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='instituicao_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='customuser',
            name='instituicao',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='instituicao_usuario', to='user.instituicao'),
        ),
        migrations.CreateModel(
            name='Planos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(help_text='Nome do plano', max_length=100)),
                ('faces', models.IntegerField(help_text='Cota total de faces para o período do plano')),
                ('reconhecimentos', models.IntegerField(help_text='Cota total de reconhecimentos para o período do plano')),
                ('valor_regular', models.DecimalField(decimal_places=2, help_text='Valor do plano', max_digits=10)),
                ('valor_promocional', models.DecimalField(decimal_places=2, help_text='Valor promocional do plano', max_digits=10)),
                ('periodo', models.IntegerField(help_text='Período em dias')),
                ('publico', models.BooleanField(default=True, help_text='Indica se o plano está disponível publicamente')),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='planos_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='planos_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Plano',
                'verbose_name_plural': 'Planos',
                'ordering': ['valor_promocional'],
            },
        ),
        migrations.CreateModel(
            name='Assinatura',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('faces', models.IntegerField(help_text='Cota total de faces para o período da assinatura')),
                ('reconhecimentos', models.IntegerField(help_text='Cota total de reconhecimentos para o período da assinatura')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('ativo', 'Ativo'), ('inativo', 'Inativo'), ('cancelado', 'Cancelado'), ('pendente', 'Pendente')], default='pendente', max_length=20)),
                ('forma_pagamento', models.CharField(blank=True, choices=[('pix', 'PIX'), ('cartao', 'Cartão de Crédito'), ('boleto', 'Boleto')], max_length=20, null=True)),
                ('data_pagamento', models.DateTimeField(blank=True, help_text='Data em que o pagamento foi confirmado', null=True)),
                ('vencimento', models.DateTimeField(blank=True, help_text='Data de término da assinatura', null=True)),
                ('id_transacao', models.CharField(blank=True, help_text='ID da transação no gateway de pagamento', max_length=100, null=True, unique=True)),
                ('codigo_fatura', models.CharField(blank=True, help_text='Código da fatura/boleto', max_length=100, null=True)),
                ('json_resposta_transacao', models.JSONField(blank=True, help_text='JSON da resposta da transação', null=True)),
                ('validacao_manual', models.BooleanField(default=False, help_text='Indica se a assinatura foi validada manualmente')),
                ('created_by', models.BigIntegerField(blank=True, help_text='ID do usuário proprietário', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_by', models.BigIntegerField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assinaturas', to=settings.AUTH_USER_MODEL)),
                ('plano', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assinaturas', to='user.planos')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TermosUso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.GenericIPAddressField()),
                ('porta', models.IntegerField(blank=True, null=True)),
                ('app', models.CharField(max_length=255)),
                ('versaodotermo', models.IntegerField()),
                ('aceite', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='termos_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='termos_updated_by', to=settings.AUTH_USER_MODEL)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='termos_usuario', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UFs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uf', models.CharField(max_length=255)),
                ('sigla_uf', models.CharField(max_length=2)),
                ('codigo_uf', models.CharField(max_length=5)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uf_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uf_updated_by', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserLogs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.GenericIPAddressField(db_index=True)),
                ('porta', models.IntegerField()),
                ('device', models.CharField(blank=True, max_length=255, null=True)),
                ('log', models.TextField()),
                ('request', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userlogs_created_by', to=settings.AUTH_USER_MODEL)),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userlogs_updated_by', to=settings.AUTH_USER_MODEL)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs_usuario', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
