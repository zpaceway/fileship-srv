build-push:
	docker buildx build --platform linux/amd64,linux/arm64 -t zpaceway/fileship-srv:latest --push .

run:
	python manage.py runserver 0.0.0.0:9898

migrations:
	python manage.py makemigrations

migrate:
	python manage.py migrate
