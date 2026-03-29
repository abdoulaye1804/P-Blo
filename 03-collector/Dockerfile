FROM python:3.11-slim

WORKDIR /app

# Dépendances d'abord pour profiter du cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Utilisateur non-root (bonne pratique sécurité)
RUN useradd -m -u 1001 collector
USER collector

EXPOSE 8000

CMD ["python", "-m", "src.main"]
