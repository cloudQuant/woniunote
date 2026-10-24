# syntax=docker/dockerfile:1

ARG UBUNTU_IMAGE=ubuntu:22.04@sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401
ARG UBUNTU_APT_SNAPSHOT=20261001T000000Z
ARG VCPKG_BASELINE=e7b524242c8a5d718a7afa26794c3c19bb8b0c71

FROM ${UBUNTU_IMAGE} AS common

ARG UBUNTU_APT_SNAPSHOT
ARG VCPKG_BASELINE

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=UTC \
    VCPKG_DISABLE_METRICS=1

LABEL com.woniunote.iteration="21" \
      com.woniunote.purpose="linux-builder" \
      com.woniunote.ubuntu="22.04" \
      com.woniunote.ubuntu-apt-snapshot="${UBUNTU_APT_SNAPSHOT}" \
      com.woniunote.vcpkg-baseline="${VCPKG_BASELINE}"

RUN set -eux; \
    rm -f /etc/apt/sources.list.d/ubuntu.sources; \
    printf 'deb https://snapshot.ubuntu.com/ubuntu/%s jammy main restricted universe multiverse\n' "$UBUNTU_APT_SNAPSHOT" > /etc/apt/sources.list; \
    printf 'deb https://snapshot.ubuntu.com/ubuntu/%s jammy-updates main restricted universe multiverse\n' "$UBUNTU_APT_SNAPSHOT" >> /etc/apt/sources.list; \
    printf 'deb https://snapshot.ubuntu.com/ubuntu/%s jammy-security main restricted universe multiverse\n' "$UBUNTU_APT_SNAPSHOT" >> /etc/apt/sources.list; \
    printf 'deb https://snapshot.ubuntu.com/ubuntu/%s jammy-backports main restricted universe multiverse\n' "$UBUNTU_APT_SNAPSHOT" >> /etc/apt/sources.list
RUN apt-get -o Acquire::https::Verify-Peer=false -o Acquire::Check-Valid-Until=false update \
    && apt-get -o Acquire::https::Verify-Peer=false install --no-install-recommends -y ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install --no-install-recommends -y \
        autoconf \
        automake \
        build-essential \
        cmake \
        curl \
        file \
        flex \
        git \
        libtool \
        ninja-build \
        pkg-config \
        python3 \
        tar \
        unzip \
        zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/source
CMD ["bash"]

FROM common AS system-libs

LABEL com.woniunote.builder="system-libs" \
      com.woniunote.drogon="1.9.8" \
      com.woniunote.trantor="1.5.21" \
      com.woniunote.jwt-cpp="0.7.0"

RUN apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install --no-install-recommends -y \
        libbrotli-dev \
        libc-ares-dev \
        libcrypt-dev \
        libfmt-dev \
        libhiredis-dev \
        libjsoncpp-dev \
        libmariadb-dev \
        libmariadb-dev-compat \
        libossp-uuid-dev \
        libpq-dev \
        libspdlog-dev \
        libsqlite3-dev \
        libssl-dev \
        libyaml-cpp-dev \
        uuid-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    multiarch="$(dpkg-architecture -qDEB_HOST_MULTIARCH)"; \
    if [ ! -e "/usr/lib/${multiarch}/libmysqlclient_r.so" ]; then \
        ln -s libmariadb.so "/usr/lib/${multiarch}/libmysqlclient_r.so"; \
    fi; \
    pkg-config --atleast-version=1.16.0 libcares; \
    curl -fsSL --retry 3 --retry-all-errors \
        "https://github.com/Thalhammer/jwt-cpp/archive/refs/tags/v0.7.0.tar.gz" \
        -o /tmp/jwt-cpp.tar.gz; \
    echo 'b9eb270e3ba8221e4b2bc38723c9a1cb4fa6c241a42908b9a334daff31137406  /tmp/jwt-cpp.tar.gz' | sha256sum --check -; \
    mkdir -p /tmp/jwt-cpp; \
    tar -xzf /tmp/jwt-cpp.tar.gz -C /tmp/jwt-cpp --strip-components=1; \
    cp -a /tmp/jwt-cpp/include/jwt-cpp /usr/local/include/; \
    curl -fsSL --retry 3 --retry-all-errors \
        "https://github.com/drogonframework/drogon/archive/refs/tags/v1.9.8.tar.gz" \
        -o /tmp/drogon.tar.gz; \
    echo '62332a4882cc7db1c7cf04391b65c91ddf6fcbb49af129fc37eb0130809e0449  /tmp/drogon.tar.gz' | sha256sum --check -; \
    mkdir -p /tmp/drogon; \
    tar -xzf /tmp/drogon.tar.gz -C /tmp/drogon --strip-components=1; \
    curl -fsSL --retry 3 --retry-all-errors \
        "https://github.com/an-tao/trantor/archive/refs/tags/v1.5.21.tar.gz" \
        -o /tmp/trantor.tar.gz; \
    echo 'c267e8d3657a85751554a6877efd1199f6766a9fd6418d2c72839ad0a8943988  /tmp/trantor.tar.gz' | sha256sum --check -; \
    mkdir -p /tmp/drogon/trantor; \
    tar -xzf /tmp/trantor.tar.gz -C /tmp/drogon/trantor --strip-components=1; \
    cmake -S /tmp/drogon -B /tmp/drogon-build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_MYSQL=ON \
        -DBUILD_REDIS=ON \
        -DBUILD_POSTGRESQL=OFF \
        -DBUILD_SQLITE=OFF; \
    cmake --build /tmp/drogon-build --parallel 2; \
    cmake --install /tmp/drogon-build; \
    ldconfig; \
    test -f /usr/local/lib/cmake/Drogon/DrogonConfig.cmake; \
    test -f /usr/local/include/jwt-cpp/jwt.h; \
    printf 'Ubuntu 22.04 system libraries\nDrogon 1.9.8\nTrantor 1.5.21\njwt-cpp 0.7.0\n' \
        > /usr/local/share/woniunote-iter21-system-libs.txt; \
    rm -rf /tmp/drogon /tmp/drogon-build /tmp/trantor.tar.gz /tmp/drogon.tar.gz /tmp/jwt-cpp /tmp/jwt-cpp.tar.gz

FROM common AS vcpkg

ARG VCPKG_BASELINE

LABEL com.woniunote.builder="vcpkg"

RUN set -eux; \
    git clone --filter=blob:none --no-checkout https://github.com/microsoft/vcpkg.git /opt/vcpkg; \
    git -C /opt/vcpkg checkout --detach "$VCPKG_BASELINE"; \
    /opt/vcpkg/bootstrap-vcpkg.sh -disableMetrics; \
    test "$(git -C /opt/vcpkg rev-parse HEAD)" = "$VCPKG_BASELINE"; \
    /opt/vcpkg/vcpkg version

# vcpkg takes a filesystem lock through this marker when invoked as the host
# UID from a bind-mounted source build; let that user acquire the lock.
RUN chmod a+rw /opt/vcpkg/.vcpkg-root

ENV VCPKG_ROOT=/opt/vcpkg
WORKDIR /workspace/source
CMD ["bash"]
