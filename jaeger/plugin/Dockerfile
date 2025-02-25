FROM golang:1.22-alpine AS build
RUN apk --no-cache add ca-certificates

WORKDIR /build/

COPY go.mod go.sum /build/
RUN go mod download
COPY . /build
RUN go build .

FROM alpine:latest AS run
RUN apk add --update --no-cache ca-certificates

COPY --from=build /build/jaeger-kusto /go/bin/jaeger-kusto
COPY --from=build /build/jaeger-kusto-config.json /config/jaeger-kusto-config.json
COPY --from=build /build/jaeger-kusto-plugin-config.json /config/jaeger-kusto-plugin-config.json

ENTRYPOINT [ "/go/bin/jaeger-kusto", "--config=/config/jaeger-kusto-plugin-config.json" ]