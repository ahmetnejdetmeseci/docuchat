FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Create migrations at runtime (apps with models), migrate, seed demo, then start ASGI
CMD ["/bin/sh", "-c", "python manage.py makemigrations uploads agent && python manage.py migrate && python manage.py init_demo && daphne -b 0.0.0.0 -p 8000 project.asgi:application"]
