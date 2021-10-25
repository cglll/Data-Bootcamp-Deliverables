FROM alpine:latest
ENV PIP_NO_CACHE_DIR=off
RUN apk add --no-cache curl jq python3 && pip3 install -q awscli

RUN cd /usr/local/bin \
    && curl -k -sS -O https://storage.googleapis.com/kubernetes-release/release/v1.12.7/bin/linux/amd64/kubectl \
    && chmod 755 /usr/local/bin/kubectl

RUN cd /usr/local/bin \
    && curl -k -sS -O https://amazon-eks.s3-us-west-2.amazonaws.com/1.12.7/2019-03-27/bin/linux/amd64/aws-iam-authenticator \
    && chmod 755 /usr/local/bin/aws-iam-authenticator

ENTRYPOINT ["kubectl"]