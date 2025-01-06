FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE='1'
ENV PYTHONUNBUFFERED='1'
ENV GUNICORN_CMD_ARGS="--timeout 10800 \
    --bind 0.0.0.0:9898 \
    --worker-connections 512 \
    --limit-request-line 0 \
    --limit-request-field_size 0 \
    --worker-class gthread \
    --threads 16 \
    --access-logfile - \
    --error-logfile -"

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /app/

RUN python manage.py collectstatic --noinput

EXPOSE 9898
CMD ["gunicorn", "fileship.wsgi:application"]
