# Dockerfile para hospedar no Hugging Face Spaces (SDK: Docker).
# Não precisa mexer no app.py: o gunicorn importa o objeto `app` direto do
# módulo (sem passar pelo bloco "if __name__ == '__main__':"), então o
# bind em 0.0.0.0:7860 é feito aqui, via linha de comando.
FROM python:3.11-slim

WORKDIR /app

# Copia só o requirements primeiro pra aproveitar cache do Docker em rebuilds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Hugging Face Spaces (SDK Docker) espera a aplicação respondendo na porta 7860.
EXPOSE 7860

# --timeout 120: a primeira pergunta depois de o container subir carrega o
# modelo de embeddings na memória (pode levar mais que os 30s padrão do
# gunicorn); as próximas requisições ficam rápidas.
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "--timeout", "120", "app:app"]
