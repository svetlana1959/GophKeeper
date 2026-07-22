BINARY := goph
GOTESTCOVERAGE_VERSION := v2.18.8

.PHONY: build run test cover cover-html cover-check tidy vet docker

build:
	go build -o bin/$(BINARY) .

run:
	go run . $(ARGS)

test:
	go test -race ./...

# Write a coverage profile (cross-package via -coverpkg) and print the total.
cover:
	go test -race -covermode=atomic -coverpkg=./... -coverprofile=coverage.out ./...
	go tool cover -func=coverage.out | tail -1

# Open the per-file coverage report in a browser.
cover-html: cover
	go tool cover -html=coverage.out

# Fail if total coverage is below the threshold in .testcoverage.yml.
cover-check: cover
	go run github.com/vladopajic/go-test-coverage/v2@$(GOTESTCOVERAGE_VERSION) --config=./.testcoverage.yml

tidy:
	go mod tidy

vet:
	go vet ./...

docker:
	docker build -t gophkeeper-cli .
