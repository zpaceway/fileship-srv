
build-push:
	docker buildx build --platform linux/amd64,linux/arm64 -t zpaceway/fileship-srv:latest --push .
