FROM python:3.11.3-slim

# Define variáveis de ambiente para evitar gravação de bytecode e buffering da saída
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala pacotes necessários para locales e configura o locale brasileiro
RUN apt-get update && \
    apt-get install -y locales && \
    sed -i -e 's/# pt_BR.UTF-8 UTF-8/pt_BR.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen pt_BR.UTF-8 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Define variáveis de ambiente de locale
ENV LANG=pt_BR.UTF-8
ENV LANGUAGE=pt_BR:pt
ENV LC_ALL=pt_BR.UTF-8

# Instala as dependências do sistema necessárias para Django e PostgreSQL
RUN apt-get update && \
    apt-get install -y \
    python3-dev \
    libpq-dev \
    build-essential \
    pkg-config \
    git \
    gcc \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Criação de usuário e diretórios necessários
RUN adduser --disabled-password appuser && \
    mkdir -p /data/web/static /data/web/media /data/web/logs && \
    chown -R appuser:appuser /data/web

# Define o diretório de trabalho
WORKDIR /app

# Copia apenas o requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências Python, incluindo explicitamente o psycopg2-binary
RUN pip install --upgrade pip && \
    pip install psycopg2-binary && \
    pip install -r requirements.txt

# Copia o resto dos arquivos do projeto
COPY . .

# Ajusta as permissões
RUN chown -R appuser:appuser /app

# A porta 8000 estará disponível para conexões externas ao container
EXPOSE 8000

# Muda para o usuário não-root
USER appuser

# Comando padrão para executar o Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]