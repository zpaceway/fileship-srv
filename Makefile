
build:
	docker build -t zpaceway/fileship-srv:latest .

run:
	docker run -d --restart always -p 9898:9898 --env-file .env --name fileship-srv -v ./db.sqlite3:/app/db.sqlite3 -v ./media/:/app/media/ zpaceway/fileship-srv:latest
