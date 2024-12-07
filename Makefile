
build:
	docker buildx build --platform linux/amd64,linux/arm64 -t zpaceway/fileship-srv:latest .

push:
	docker push zpaceway/fileship-srv:latest
