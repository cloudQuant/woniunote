# syntax=docker/dockerfile:1

ARG SYSTEM_LIBS_IMAGE=woniunote.iter21/system-libs:ubuntu22.04
FROM ${SYSTEM_LIBS_IMAGE}

ARG SYSTEM_LIBS_IMAGE
ARG SYSTEM_LIBS_IMAGE_ID
ARG RUNTIME_SPEC_SHA256

LABEL com.woniunote.iteration="21" \
      com.woniunote.purpose="backend-runtime" \
      com.woniunote.runtime.base-image="${SYSTEM_LIBS_IMAGE}" \
      com.woniunote.runtime.base-image-id="${SYSTEM_LIBS_IMAGE_ID}" \
      com.woniunote.runtime.spec-sha256="${RUNTIME_SPEC_SHA256}"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends -y iproute2 socat \
    && rm -rf /var/lib/apt/lists/*

COPY container-entrypoint.sh /usr/local/bin/woniunote-iter21-container-entrypoint
RUN chmod 0755 /usr/local/bin/woniunote-iter21-container-entrypoint

WORKDIR /
ENTRYPOINT ["/usr/local/bin/woniunote-iter21-container-entrypoint"]
