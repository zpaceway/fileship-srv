FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE='1'
ENV PYTHONUNBUFFERED='1'
ENV GUNICORN_CMD_ARGS='--timeout 1200 --worker-connections 1000 --limit-request-line 0 --limit-request-field_size 0'

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /app/

RUN python manage.py collectstatic --noinput
RUN apt-get update && apt-get install -y gcc

EXPOSE 9898
CMD ["gunicorn", "--bind", "0.0.0.0:9898", "fileship.wsgi:application"]
