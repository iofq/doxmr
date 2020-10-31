FROM alpine:latest
ENV TERRAFORM_VERSION=0.13.5

RUN apk --no-cache update && apk add --no-cache openssh-client ansible py3-requests python3 curl unzip && \
  curl -O https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
  unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
  cp terraform /usr/local/bin/ && \
  rm terraform* && \
  apk del curl unzip 

VOLUME /app
WORKDIR /app

# ENTRYPOINT ["python3"]
# CMD ["doxmr.py"]
