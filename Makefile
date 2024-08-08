run:
	python manage.py runserver 0.0.0.0:9898

migrations:
	python manage.py makemigrations

migrate:
	python manage.py migrate

install:
	sudo apt install p7zip-full --install-suggests
