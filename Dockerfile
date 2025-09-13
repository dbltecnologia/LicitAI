# Dockerfile Profissional para LicitAI
# Utiliza uma abordagem multi-stage para criar uma imagem final otimizada e segura.

# --- ESTÁGIO 1: Build ---
# Usamos uma imagem completa para instalar as dependências de compilação, se necessário.
# Isto mantém a imagem final leve, pois estas dependências não serão incluídas.
FROM python:3.12-slim as builder

# Define o diretório de trabalho
WORKDIR /app

# Atualiza o pip e instala as dependências
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir=/app/wheels -r requirements.txt

# --- ESTÁGIO 2: Final ---
# Começamos com uma nova imagem base limpa para o ambiente de produção.
FROM python:3.12-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia as dependências pré-compiladas do estágio de build.
# Isto é mais rápido e eficiente do que instalar tudo novamente.
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# Copia o código da aplicação para o container.
# Separar a cópia das dependências da cópia do código aproveita melhor o cache do Docker.
COPY . .

# --- Configuração de Segurança e Ambiente (MELHORES PRÁTICAS) ---
# NUNCA copie ficheiros de credenciais (como firebase-admin.json) para a imagem.
# As credenciais devem ser geridas pelo ambiente onde o container é executado.

# 1. Autenticação Google Cloud:
#    O utilizador deve autenticar-se no ambiente hospedeiro usando a gcloud CLI.
#    O container irá herdar estas credenciais através de um volume montado.
#    Exemplo de execução:
#    docker run -v ~/.config/gcloud:/root/.config/gcloud ...

# 2. Chave de API Gemini:
#    A chave da API deve ser passada como uma variável de ambiente no momento da execução.
#    Isto evita que a chave fique "hardcoded" na imagem.
#    -e GEMINI_API_KEY="sua_chave_aqui"

# Exemplo de comando de execução completo:
# docker build -t licitai .
# docker run --rm -it \
#   -e GEMINI_API_KEY="SUA_CHAVE_AQUI" \
#   -v ~/.config/gcloud:/root/.config/gcloud \
#   licitai python main.py diagnostico

# Comando padrão que será executado se nenhum outro for especificado.
CMD ["python", "main.py", "diagnostico"]
