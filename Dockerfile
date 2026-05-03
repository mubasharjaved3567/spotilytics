FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y default-jdk curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/default-java

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY . .

RUN mkdir -p data/raw data/processed logs ml/models

EXPOSE 8000

CMD ["uvicorn", "serving.main:app", "--host", "0.0.0.0", "--port", "8000"]