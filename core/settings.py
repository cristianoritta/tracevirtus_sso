#core/settings.py

from pathlib import Path
import os
from dotenv import load_dotenv

# Configurações básicas do projeto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data' / 'web'

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

AUTH_USER_MODEL = 'user.CustomUser'

# Segurança
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [
    h.strip() for h in os.getenv('ALLOWED_HOSTS', '').split(',')
    if h.strip()
]

# Use o cabeçalho X-Forwarded-Host para reconhecer o nome do host original
USE_X_FORWARDED_HOST = os.getenv('USE_X_FORWARDED_HOST', 'False') == 'True'

# Parse a variável SECURE_PROXY_SSL_HEADER e converta em tupla
secure_proxy_ssl_header_raw = os.getenv('SECURE_PROXY_SSL_HEADER', 'HTTP_X_FORWARDED_PROTO, https')
SECURE_PROXY_SSL_PROTO, SECURE_PROXY_SSL_HEADER_VALUE = map(str.strip, secure_proxy_ssl_header_raw.split(','))
SECURE_PROXY_SSL_HEADER = (SECURE_PROXY_SSL_PROTO, SECURE_PROXY_SSL_HEADER_VALUE)

# Usar cookies seguros
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Defina as origens confiáveis para a verificação CSRF
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

# Configuração de Aplicativos
INSTALLED_APPS = [
    'user',
    'core',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',
    'user_agents'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'middleware.auth_middleware.AuthMiddleware',
    'middleware.user_logs.UserLogsMiddleware',
    'middleware.completa_cadastro.CadastroMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processor.app_name',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

if os.getenv('ENVIRONMENT') == 'prod':
    DATABASES = {
        'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.mysql'),
        'NAME': os.getenv('MYSQL_DB', ''),
        'USER': os.getenv('MYSQL_USER', ''),
        'PASSWORD': os.getenv('MYSQL_PASSWORD', ''),
        'HOST': os.getenv('MYSQL_HOST', 'localhost'),
        'PORT': os.getenv('MYSQL_PORT', '3306'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Validação de Senha
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Localização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# Arquivos Estáticos
STATIC_URL = '/static/'
STATIC_ROOT = DATA_DIR / 'static'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Arquivos de Media
MEDIA_URL = '/media/'
MEDIA_ROOT = DATA_DIR / 'media'

# Configuração para uploads grandes
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800 # 50 * 1024 * 1024 bytes para 50 MB

# PAGAMENTO
PAGAMENTOS_API_ENDPOINT = os.getenv('PAGAMENTOS_API_ENDPOINT')
AUTHORIZATION_HEADER_VALUE = os.getenv('AUTHORIZATION_HEADER_VALUE')

#CONFIG EMAIL
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'change-me')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'change-me')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'change-me')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False') == 'True'

# Whatsapp
WA_API_ENDPOINT = os.getenv('WA_API_ENDPOINT')
WA_API_KEY = os.getenv('WA_API_KEY')
WA_GROUP_ADM = os.getenv('WA_GROUP_ADM')

# Configuração do Django para PKs automáticas
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#CONFIGURAÇÃO DO SSO
CLIENT_ID = os.getenv('CLIENT_ID', '')
CLIENT_SECRET = os.getenv('CLIENT_SECRET', '')
REDIRECT_URI = os.getenv('REDIRECT_URI', '')
SSO_SERVER = os.getenv('SSO_SERVER', '')
CODE_VERIFIER = os.getenv('CODE_VERIFIER', '')
CODE_CHALLENGE = os.getenv('CODE_CHALLENGE', '')

#CONFIGURAÇÃO DO TELEGRAM
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')

#CONFIGURAÇÃO DO APP
APP_NAME = os.getenv('APP_NAME', '')

# Configuração de Logging
ERRO_MSG = os.getenv('ERRO_MSG', 'false').lower() == 'true'

# Configuração base dos handlers
handlers = ['console', 'file']
if ERRO_MSG:
    handlers.append('telegram')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'standard': {
            'format': '[{asctime}] - {levelname} - {name} - {filename}:({lineno}): {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'app.log'),
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
            'formatter': 'standard',
        },
        'telegram': {
            'level': 'ERROR',
            'class': 'utils.telegram_log_handler.TelegramLogHandler',
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django': {
            'handlers': handlers,
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': handlers,
        'level': 'WARNING',
    },
}

# Garantir que o diretório de logs existe
os.makedirs(os.path.join(BASE_DIR, 'logs'), exist_ok=True)
