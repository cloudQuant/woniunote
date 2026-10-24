ARG BASE_IMAGE=woniunote.iter21/system-libs:ubuntu22.04
FROM ${BASE_IMAGE}

ARG RUN_ID

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC

RUN apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install --no-install-recommends -y \
        curl \
        nodejs \
        nginx \
        openssl \
        procps \
        ssl-cert \
        systemd \
        systemd-sysv \
    && rm -rf /var/lib/apt/lists/*

LABEL org.woniunote.iter21.run-id="${RUN_ID}" \
      org.woniunote.iter21.service="deploy-runtime-image"

RUN mkdir -p /opt/woniunote-iter21-runtime/bin \
             /opt/woniunote-iter21-runtime/input \
             /var/lib/woniunote-iter21-data

COPY container/ /opt/woniunote-iter21-runtime/
RUN chmod 0755 /opt/woniunote-iter21-runtime/*.sh \
              /opt/woniunote-iter21-runtime/bin/*

STOPSIGNAL SIGRTMIN+3
ENTRYPOINT ["/sbin/init"]
