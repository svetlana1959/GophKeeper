BINARY := goph

.PHONY: build run test tidy vet docker

build:
	go build -o bin/$(BINARY) .

run:
	go run . $(ARGS)

test:
	go test ./...

tidy:
	go mod tidy

vet:
	go vet ./...

docker:
	docker build -t gophkeeper-cli .
