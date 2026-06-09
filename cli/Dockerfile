# syntax=docker/dockerfile:1

# --- build stage ---
FROM golang:1.26 AS build
WORKDIR /src

# Cache module downloads.
COPY go.mod go.sum ./
RUN go mod download

COPY . .
# Static, pure-Go build (no CGO) so it runs on a minimal base image.
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/goph .

# --- runtime stage ---
FROM alpine:3.20
RUN useradd -m goph
USER goph
WORKDIR /home/goph
COPY --from=build /out/goph /usr/local/bin/goph
ENTRYPOINT ["goph"]
CMD ["--help"]
