FROM debian:latest
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update && apt-get -y install ansible python3 python3-pip curl
RUN curl -fsSL https://apt.releases.hashicorp.com/gpg | apt-key add - && \
  apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" && \
  apt-get -y update && apt-get -y install terraform

