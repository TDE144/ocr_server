FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y

RUN pip install --no-cache-dir -r requirements.txt

COPY . .


CMD ["python3", "main.py"]