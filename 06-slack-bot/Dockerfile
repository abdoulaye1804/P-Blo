FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN useradd -m -u 1001 slackbot
USER slackbot

EXPOSE 3000

CMD ["python", "-m", "src.main"]
