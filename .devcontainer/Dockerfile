FROM mcr.microsoft.com/devcontainers/python:3.12

RUN apt-get update \
    && apt-get install -y --no-install-recommends unzip \
    && DART_ARCH=$(dpkg --print-architecture) \
    && curl -fsSL "https://storage.googleapis.com/dart-archive/channels/stable/release/latest/sdk/dartsdk-linux-${DART_ARCH}-release.zip" \
       -o /tmp/dart-sdk.zip \
    && unzip -q /tmp/dart-sdk.zip -d /usr/local \
    && rm /tmp/dart-sdk.zip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/local/dart-sdk/bin:${PATH}"
