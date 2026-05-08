FROM python:3.11-slim

# Evita gerar arquivos .pyc
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copia dependências primeiro (melhor cache)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do projeto
COPY . .

EXPOSE 5002

CMD ["python", "run.py"]